import pytest
from canonical_project_slots import canonical_name,match_projects,AmbiguousProject


def test_case_and_unicode_normalization():
    assert canonical_name('  Me  &  You  ')=='me & you'
    assert canonical_name('ＣＡＦＥ́')=='café'


def test_same_name_is_stable_and_kind_scoped():
    video={'kind':'video','path':'/owner/a.zuckervid','name':'My Song'}
    audio={'kind':'audio','id':'b'*32,'name':'My Song'}
    assert match_projects([video,audio],'  my   SONG ',kind='video')['project']['path']==video['path']
    assert match_projects([video,audio],'My Song',kind='audio')['project']['id']==audio['id']
    assert match_projects([video],'Different')['action']=='new'


def test_conflicts_are_not_silently_resolved():
    a={'path':'/owner/a.zuckervid','name':'Song'}
    b={'path':'/owner/b.zuckervid','name':'song'}
    with pytest.raises(AmbiguousProject):match_projects([a,b],'SONG')
    assert match_projects([a,a],'Song')['action']=='open'


def test_invalid_titles_and_entries():
    for title in ['', ' '*4, 'X'*121, 'bad\x00title']:
        with pytest.raises(ValueError):canonical_name(title)
    with pytest.raises(ValueError):match_projects([{'name':'Song'}],'Song')
    with pytest.raises(ValueError):match_projects([],'Song',kind='bad')
