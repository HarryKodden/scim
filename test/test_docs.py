
# import test_docs.py

def test_apidoc(test_app):
    response = test_app.get("/")
    assert response.status_code == 200
