def test_csv_import_validation_and_duplicate_handling(client, auth_headers):
    csv_data = "amount,description,category,date,notes\n12.50,Lunch,Food,2026-09-01,Office\nnope,Broken,Food,2026-09-02,\n12.50,Lunch,Food,2026-09-01,Office\n"
    response = client.post('/api/expenses/import', headers=auth_headers, files={'file':('expenses.csv', csv_data, 'text/csv')})
    assert response.status_code == 200
    assert response.json()['imported'] == 1
    assert response.json()['skipped_duplicates'] == 1
    assert response.json()['failed'] == 1
    listing = client.get('/api/expenses', headers=auth_headers).json()
    assert listing['total'] == 1


def test_csv_export(client, auth_headers):
    assert client.post('/api/expenses', headers=auth_headers, json={'amount':'10.00','description':'Bus','category':'Transport','date':'2026-09-10','notes':'Morning'}).status_code == 201
    response = client.get('/api/expenses/export/csv', headers=auth_headers)
    assert response.status_code == 200
    assert 'amount,description,category,date,notes' in response.text
    assert '10.00,Bus,Transport,2026-09-10,Morning' in response.text
