"""
MongoDB document structure (no ORM).
Collections: users (username, password_hash, display_name, created_at),
assets (user_id, symbol, name, exchange, asset_type, created_at),
purchases (asset_id, price_per_unit, quantity, purchase_date, notes, created_at).
Documents use _id (ObjectId); in API/templates we use string ids.
"""
