import pytest
import requests
from app.models.user import User
from app.core.security import hash_password, create_access_token

@pytest.fixture
def agent_token(app, mock_db_client):
    user = User(
        full_name="Agent User",
        email="agent@test.com",
        password_hash=hash_password("password"),
        role="AGENT"
    )
    mock_db_client.collection("users").document(user.id).set(user.to_dict())
    return create_access_token(user_id=user.id, role="AGENT")

def test_proxy_media_rejects_malformed_media_id_without_calling_meta(client, agent_token, mocker):
    """
    Meta media IDs are numeric. A malformed id must be rejected with 400
    before it's ever forwarded to Meta's API with our access token.
    """
    client.set_cookie("access_token", agent_token)
    mock_get = mocker.patch("requests.get")

    response = client.get('/api/media/not-a-valid-id;rm -rf')

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    mock_get.assert_not_called()

def test_proxy_media_does_not_leak_raw_meta_error_body(client, agent_token, mocker):
    """
    Meta's raw error response body must not be relayed verbatim to the
    client -- log it server-side and return a generic message instead.
    """
    client.set_cookie("access_token", agent_token)

    err_response = requests.Response()
    err_response.status_code = 401
    err_response._content = b'{"error": {"message": "Invalid OAuth access token: super-secret-detail"}}'
    http_error = requests.exceptions.HTTPError(response=err_response)
    mocker.patch("requests.get", side_effect=http_error)

    response = client.get('/api/media/123456789012345')

    assert response.status_code == 401
    body = response.get_json()
    assert body["status"] == "error"
    assert "super-secret-detail" not in body["message"]

def test_proxy_media_sets_content_disposition_when_download_requested(client, agent_token, mocker, monkeypatch):
    monkeypatch.setattr("app.api.media.WHATSAPP_ACCESS_TOKEN", "fake_token")
    client.set_cookie("access_token", agent_token)

    meta_info_resp = mocker.Mock(status_code=200)
    meta_info_resp.json.return_value = {
        "url": "https://lookaside.fbsbx.com/fake_download_url",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    meta_info_resp.raise_for_status.return_value = None

    download_resp = mocker.Mock(status_code=200)
    download_resp.iter_content.return_value = [b"fake-excel-data"]
    download_resp.raise_for_status.return_value = None

    mocker.patch("requests.get", side_effect=[meta_info_resp, download_resp])

    response = client.get('/api/media/1234567890?filename=Assignment_Devanshu.xlsx&download=1')
    assert response.status_code == 200
    assert response.data == b"fake-excel-data"
    cd = response.headers.get("Content-Disposition")
    assert cd is not None
    assert "attachment" in cd
    assert "Assignment_Devanshu.xlsx" in cd

def test_proxy_media_sanitizes_filename_against_header_injection(client, agent_token, mocker, monkeypatch):
    monkeypatch.setattr("app.api.media.WHATSAPP_ACCESS_TOKEN", "fake_token")
    client.set_cookie("access_token", agent_token)

    meta_info_resp = mocker.Mock(status_code=200)
    meta_info_resp.json.return_value = {
        "url": "https://lookaside.fbsbx.com/fake_download_url",
        "mime_type": "application/pdf"
    }
    meta_info_resp.raise_for_status.return_value = None

    download_resp = mocker.Mock(status_code=200)
    download_resp.iter_content.return_value = [b"fake-pdf-data"]
    download_resp.raise_for_status.return_value = None

    mocker.patch("requests.get", side_effect=[meta_info_resp, download_resp])

    response = client.get('/api/media/1234567890?filename=test%0d%0aInjected-Header:bad.pdf&download=1')
    assert response.status_code == 200
    cd = response.headers.get("Content-Disposition")
    assert "\r" not in cd
    assert "\n" not in cd
    assert "Injected-Header" not in response.headers
