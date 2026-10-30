"""执行真实 skill 脚本，仅隔离外部 HTTP。"""
import json
import os
from pathlib import Path
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'generators/web_skill_assets/scripts'


def run_script(name, args, scripts=SCRIPTS):
    code = '''
    globalThis.fetch = async (url, init) => ({ok:true,
      json:async()=>({url, body:init.body ? JSON.parse(init.body) : null})});
    process.argv[2] = process.env.TEST_ARGS;
    await import(process.env.TEST_SCRIPT);
    '''
    return subprocess.run(['node', '--input-type=module', '-e', code],
        env={**os.environ, 'SCIVERSE_API_TOKEN': 'test-only',
             'SCIVERSE_BASE_URL': 'https://api.sciverse.space',
             'TEST_SCRIPT': (scripts / f'{name}.mjs').as_uri(),
             'TEST_ARGS': json.dumps(args)}, text=True, capture_output=True)


@pytest.mark.parametrize('collection', ['papers', 'authors', 'sources', 'patents'])
def test_metadata_canonical_payload_without_implicit_sort(collection):
    args = {'collection': collection, 'filters': [{'field': 'x', 'operator': 'FILTER_OP_EQ', 'value': 0}],
            'sort': [{'field': 'x', 'order': 'SORT_ORDER_ASC'}]}
    result = run_script('search_metadata', args)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['body'] == args


def test_metadata_defaults_papers():
    result = run_script('search_metadata', {})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['body'] == {'collection': 'papers'}


@pytest.mark.parametrize('args', [{'typo': 1}, {'filters_advanced': []}, {'year_from': 2020},
                                 {'collection': 'unknown'}, [], None])
def test_metadata_rejects_invalid_args_before_http(args):
    result = run_script('search_metadata', args)
    assert result.returncode == 2, result.stderr
    assert result.stdout == ''


@pytest.mark.parametrize('collection', ['authors', 'sources', 'patents'])
def test_legacy_nonpaper_never_adds_year_sort(collection):
    result = run_script('search_papers', {'collection': collection})
    assert result.returncode == 0, result.stderr
    assert 'sort' not in json.loads(result.stdout)['body']


@pytest.mark.parametrize('collection', ['authors', 'sources', 'patents'])
@pytest.mark.parametrize('mode', ['none', 'auto'])
@pytest.mark.parametrize('sort_key', [None, 'sort', 'sort_advanced'])
def test_legacy_nonpaper_allows_neutral_year_sort(collection, mode, sort_key):
    args = {'collection': collection, 'sort_by_year': mode}
    explicit_sort = [{'field': 'catalog_sort_field', 'order': 'SORT_ORDER_DESC'}]
    if sort_key:
        args[sort_key] = explicit_sort
    result = run_script('search_papers', args)
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)['body']
    assert body == ({'collection': collection, 'sort': explicit_sort}
                    if sort_key else {'collection': collection})


@pytest.mark.parametrize('collection', ['authors', 'sources', 'patents'])
@pytest.mark.parametrize('mode', ['asc', 'desc'])
def test_legacy_nonpaper_rejects_explicit_year_sort(collection, mode):
    result = run_script('search_papers', {'collection': collection, 'sort_by_year': mode})
    assert result.returncode == 2, result.stderr
    assert result.stdout == ''


@pytest.mark.parametrize('key,value', [('authors', ['x']), ('year_from', 2020),
    ('year_to', 2024), ('journals', []), ('subjects', []), ('title_contains', 'x'),
    ('abstract_contains', 'x')])
def test_legacy_rejects_nonpaper_convenience(key, value):
    result = run_script('search_papers', {'collection': 'patents', key: value})
    assert result.returncode == 2, result.stderr


def test_legacy_paper_translation_unchanged():
    result = run_script('search_papers', {'authors': ['Hinton'], 'year_from': 2020,
        'filters_advanced': [{'field': 'doi', 'value': 'x'}]})
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)['body']
    assert body['filters'] == [
        {'field': 'author', 'operator': 'FILTER_OP_IN', 'value': ['Hinton']},
        {'field': 'publication_published_year', 'operator': 'FILTER_OP_GTE', 'value': 2020},
        {'field': 'doi', 'operator': 'FILTER_OP_EQ', 'value': 'x'}]
    assert body['sort'] == [{'field': 'publication_published_year', 'order': 'SORT_ORDER_DESC'}]


def test_legacy_canonical_sort_takes_precedence_over_auto_year():
    sort = [{'field': 'citation_count', 'order': 'SORT_ORDER_DESC'}]
    result = run_script('search_papers', {'sort': sort})
    assert json.loads(result.stdout)['body']['sort'] == sort


@pytest.mark.parametrize('collection', [None, 'papers', 'patents'])
def test_content_collection_and_defaults(collection):
    from urllib.parse import urlparse, parse_qs
    args = {'doc_id': 'abc'}
    if collection:
        args['collection'] = collection
    result = run_script('read_content', args)
    assert result.returncode == 0, result.stderr
    query = parse_qs(urlparse(json.loads(result.stdout)['url']).query)
    assert query == {'doc_id': ['abc'], 'collection': [collection or 'papers'],
                     'offset': ['0'], 'limit': ['4096']}


def test_content_keeps_explicit_window():
    result = run_script('read_content', {'doc_id': 'abc', 'offset': 3, 'limit': 12})
    assert result.returncode == 0, result.stderr
    assert 'offset=3' in json.loads(result.stdout)['url']
    assert 'limit=12' in json.loads(result.stdout)['url']


def test_content_rejects_authors():
    assert run_script('read_content', {'doc_id': 'abc', 'collection': 'authors'}).returncode == 2


@pytest.mark.parametrize('generator,bundle', [
    ('to_clawhub_skill', 'clawhub'),
    ('to_claude_skill', 'skill-claude-code/skills/sciverse'),
])
def test_build_entrypoint_packages_executable_scripts(tmp_path, monkeypatch, generator, bundle):
    import importlib
    module = importlib.import_module(f'generators.{generator}')
    # 真实 main，输出重定向临时目录，不触碰待统一生成的发布目录。
    (tmp_path / 'clawhub').mkdir()
    (tmp_path / 'openapi.yaml').write_bytes(
        (SCRIPTS.parents[2] / 'openapi.yaml').read_bytes())
    monkeypatch.setattr(module, '__file__', str(tmp_path / 'generators' / f'{generator}.py'))
    module.main()
    scripts = tmp_path / bundle / 'scripts'
    assert (scripts / 'search_metadata.mjs').is_file()
    assert (scripts / 'search_papers.mjs').is_file()
    result = run_script('search_metadata', {'collection': 'patents'}, scripts)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['body'] == {'collection': 'patents'}
    result = run_script('read_content', {'doc_id': 'abc', 'collection': 'patents'}, scripts)
    assert result.returncode == 0, result.stderr
    assert 'limit=4096' in json.loads(result.stdout)['url']


@pytest.mark.parametrize('extra', [{}, {'cursor': 'opaque-next-page'},
    {'cursor': 'opaque-next-page', 'sort': [{'field': 'citation_count', 'order': 'SORT_ORDER_DESC'}]}])
def test_clawhub_legacy_preserves_canonical_payload_and_cursor(tmp_path, extra):
    from generators.to_web_skill import copy_scripts
    scripts = tmp_path / 'scripts'
    copy_scripts(scripts, channel='openclaw')
    args = {'filters': [{'field': 'publication_published_year',
                         'operator': 'FILTER_OP_GTE', 'value': 2020}], **extra}
    result = run_script('search_papers', args, scripts)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['body'] == args


@pytest.mark.parametrize('channel', ['skills', 'openclaw'])
def test_packaged_metadata_keeps_no_implicit_sort_with_cursor(tmp_path, channel):
    from generators.to_web_skill import copy_scripts
    scripts = tmp_path / 'scripts'
    copy_scripts(scripts, channel=channel)
    args = {'collection': 'papers', 'cursor': 'opaque-next-page',
            'filters': [{'field': 'publication_published_year',
                         'operator': 'FILTER_OP_GTE', 'value': 2020}]}
    result = run_script('search_metadata', args, scripts)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['body'] == args
