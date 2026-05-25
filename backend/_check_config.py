"""Check current model configs from DB."""
import asyncio, sys
sys.path.insert(0, '.')
from app.db import db

async def get():
    await db.init_db()
    conn = await db.get_connection()
    cur = await conn.execute('SELECT * FROM model_configs ORDER BY created_at DESC')
    rows = await cur.fetchall()
    for r in rows:
        d = dict(r)
        print('name:', d['name'])
        print('base_url:', d['base_url'])
        print('model_name:', d['model_name'])
        print('provider:', d['provider'])
        print('api_key:', d.get('api_key', '')[:8] + '...' if d.get('api_key') else 'None')
        print('is_default:', d['is_default'])
        print('---')

asyncio.run(get())
