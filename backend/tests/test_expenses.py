def create(client, headers, amount, description, category='Food', date='2026-09-15'):
    return client.post('/api/expenses', headers=headers, json={'amount': amount, 'description': description, 'category': category, 'date': date, 'notes': None})


def test_crud_and_ownership(client):
    headers = {'Authorization': f"Bearer {client.post('/api/auth/register', json={'email':'a@example.com','password':'password123'}).json()['access_token']}"}
    other = client.post('/api/auth/register', json={'email':'b@example.com','password':'password123'}).json()['access_token']
    created = create(client, headers, '42.50', 'Groceries')
    assert created.status_code == 201
    expense_id = created.json()['id']
    fetched = client.get(f'/api/expenses/{expense_id}', headers=headers)
    assert fetched.status_code == 200 and fetched.json()['amount'] == '42.50'
    edited = client.patch(f'/api/expenses/{expense_id}', headers=headers, json={'amount':'50.00','description':'Weekly groceries'})
    assert edited.status_code == 200 and edited.json()['amount'] == '50.00'
    assert client.get(f'/api/expenses/{expense_id}', headers={'Authorization':f'Bearer {other}'}).status_code == 404
    assert client.delete(f'/api/expenses/{expense_id}', headers=headers).status_code == 204
    assert client.get(f'/api/expenses/{expense_id}', headers=headers).status_code == 404


def test_filter_search_and_pagination(client, auth_headers):
    for i in range(25):
        response = create(client, auth_headers, str(i + 1), f'Coffee {i}', 'Food' if i % 2 else 'Transport')
        assert response.status_code == 201
    response = client.get('/api/expenses', headers=auth_headers, params={'page':2,'page_size':10,'category':'Food'})
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 12
    assert len(data['items']) == 2
    search = client.get('/api/expenses', headers=auth_headers, params={'search':'Coffee 24'})
    assert search.status_code == 200 and search.json()['total'] == 1
