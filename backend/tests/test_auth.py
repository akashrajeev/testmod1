def test_register_and_login(client):
    registered = client.post('/api/auth/register', json={'email': 'bob@example.com', 'password': 'password123'})
    assert registered.status_code == 201
    assert registered.json()['access_token']
    duplicate = client.post('/api/auth/register', json={'email': 'bob@example.com', 'password': 'password123'})
    assert duplicate.status_code == 409
    login = client.post('/api/auth/login', json={'email': 'bob@example.com', 'password': 'password123'})
    assert login.status_code == 200
    bad = client.post('/api/auth/login', json={'email': 'bob@example.com', 'password': 'wrongpassword'})
    assert bad.status_code == 401


def test_protected_endpoint_requires_auth(client):
    response = client.get('/api/expenses')
    assert response.status_code == 401
