
def test_auth(test_app):
    headers = {
      'x-api-key': "wrong"
    }

    response = test_app.get("/Users", headers=headers)
    assert response.status_code == 401


def test_bearer(test_app):
    headers = {
      'Authorization': "Bearer secret"
    }

    response = test_app.get("/Users", headers=headers)
    assert response.status_code == 200
