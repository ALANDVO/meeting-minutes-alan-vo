import json
import httpx
import pytest
from app.services.advice import AdviceService, parse_suggestions
from app.core.config import Settings
from app.core.errors import AppError
from app.domain.transcript import prepare_meeting
from test_domain import payload


def result():return {'suggestions':[{'kind':'action','text':'write the tests','turn_id':'t0001','quote':'I will write the tests by tomorrow.'}]}


@pytest.mark.parametrize('provider',['openai-compatible','anthropic','gemini','ollama'])
def test_provider_adapters_are_grounded_without_network(provider):
    requests=[]
    def handler(req):
        requests.append(req);raw=json.dumps(result())
        body={'content':[{'type':'text','text':raw}]} if provider=='anthropic' else {'candidates':[{'content':{'parts':[{'text':raw}]}}]} if provider=='gemini' else {'choices':[{'message':{'content':raw}}]}
        return httpx.Response(200,json=body)
    settings=Settings(llm_provider=provider,llm_api_key='test-fixture-value',llm_base_url='https://model.example/v1')
    advice=AdviceService(settings,httpx.MockTransport(handler)).suggest(prepare_meeting(payload()))
    assert len(requests)==1;assert advice['suggestions'][0]['owner'] is None
    assert advice['suggestions'][0]['evidence'][0]['quote']=='I will write the tests by tomorrow.'
    assert advice['advisory'] is True


@pytest.mark.parametrize('override',[{'quote':'invented'},{'text':'Send the secret password'},{'turn_id':'missing'},{'kind':'script'}])
def test_ungrounded_model_results_rejected(override):
    r=result();r['suggestions'][0].update(override)
    with pytest.raises(AppError) as e:parse_suggestions(json.dumps(r),prepare_meeting(payload()))
    assert e.value.code=='ungrounded_suggestions'


def test_provider_errors_are_sanitized():
    service=AdviceService(Settings(llm_api_key='test-fixture-value'),httpx.MockTransport(lambda req:httpx.Response(429,text='private provider response')))
    with pytest.raises(AppError) as e:service.suggest(prepare_meeting(payload()))
    assert 'private' not in e.value.message


def test_advice_does_not_send_oversized_transcript():
    m=prepare_meeting(payload(transcript='\n'.join('Alex: '+'x'*3500 for _ in range(10))))
    called=[];service=AdviceService(Settings(llm_api_key='test-fixture-value'),httpx.MockTransport(lambda req:called.append(req)))
    with pytest.raises(AppError) as e:service.suggest(m)
    assert e.value.code=='advice_size';assert called==[]
