import pytest
from larsana.mime import nginx_mime_types

BASE = '''types {
    application/javascript js;
    text/css css;
    application/pdf pdf;
}
'''


def test_module_and_worker_mime_patch_is_idempotent():
    patched = nginx_mime_types(BASE)
    assert 'application/javascript js mjs;' in patched
    assert nginx_mime_types(patched) == patched
    assert patched.count('mjs') == 1
    assert 'text/css css;' in patched and 'application/pdf pdf;' in patched


def test_existing_text_javascript_mapping_is_kept():
    source = BASE.replace('application/javascript js;', 'text/javascript js mjs;')
    assert nginx_mime_types(source) == source


def test_wrong_or_duplicate_vendor_mjs_mappings_are_corrected():
    source = BASE.replace('text/css css;', 'text/css css mjs;').replace('application/pdf pdf;', 'application/pdf pdf mjs;')
    patched = nginx_mime_types(source)
    assert patched.count('mjs') == 1
    assert 'application/javascript js mjs;' in patched


def test_user_override_exclusions_do_not_remove_other_defaults():
    patched = nginx_mime_types(BASE, exclude={'mjs'})
    assert 'mjs' not in patched and 'application/javascript js;' in patched
    assert 'text/css css;' in patched
    assert nginx_mime_types(patched, exclude={'mjs'}) == patched


def test_unrecognized_vendor_table_fails_explicitly():
    with pytest.raises(ValueError, match='no JavaScript mapping'):
        nginx_mime_types('types { text/css css; }')
