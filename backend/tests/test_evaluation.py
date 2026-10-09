from app.services.evaluation import evaluate


def test_diagnostic_exposes_known_failures_instead_of_claiming_perfection():
    report=evaluate()
    assert report['cases']==24
    assert report['false_positive']>=3 and report['false_negative']>=3
    assert 0<report['precision']<1 and 0<report['recall']<1
    assert report['limitations']
    assert sum(not r['correct'] for r in report['rows'])==report['false_positive']+report['false_negative']


def test_diagnostic_is_reproducible():assert evaluate()==evaluate()
