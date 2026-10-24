"""One-off cleanup: remove all dummy_* accounts and any data they created.

Also reverses net inventory/menu-stock impact caused by those dummies so
materials and menu stock go back to their pre-dummy baseline (floored at 0).

Usage: python3 cleanup_dummy_accounts.py [--dry]
"""
import asyncio, os, sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")


async def main(dry_run=False):
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]

    dummies = await db.users.find({"username": {"$regex": "^dummy_"}}).to_list(50)
    if not dummies:
        print("No dummy users found.")
        return

    obj_ids = [d["_id"] for d in dummies]
    str_oids = [str(d["_id"]) for d in dummies]
    uuids = [d.get("id") for d in dummies if d.get("id")]
    names = [d.get("name") for d in dummies if d.get("name")]
    usernames = [d.get("username") for d in dummies if d.get("username")]
    all_user_refs = list(set(uuids + str_oids))
    name_tags = list(set(names + usernames))
    print(f"Found {len(dummies)} dummy users: {usernames}")

    # --- 1) Reverse net inventory impact on materials -----------------------
    inv_txs = await db.inventory_tx.find({
        "$or": [{"user": {"$in": name_tags}}, {"user_id": {"$in": all_user_refs}}]
    }).to_list(5000)
    delta_by_mat: dict[str, float] = {}
    for t in inv_txs:
        mid = t.get("material_id")
        if not mid:
            continue
        qty = float(t.get("qty") or 0)
        sign = 1 if t.get("type") == "in" else -1
        delta_by_mat[mid] = delta_by_mat.get(mid, 0.0) + sign * qty
    print(f"\nReversing inventory on {len(delta_by_mat)} materials:")
    for mid, delta in delta_by_mat.items():
        if delta == 0:
            continue
        m = await db.materials.find_one({"id": mid})
        if not m:
            continue
        cur = float(m.get("stock") or 0)
        new = max(0.0, cur - delta)
        print(f"  {m.get('name')}: {cur} - {delta} -> {new}")
        if not dry_run:
            await db.materials.update_one({"id": mid}, {"$set": {"stock": new}})

    # --- 2) Reverse net menu stock impact ----------------------------------
    menu_txs = await db.menu_stock_tx.find({
        "$or": [{"user": {"$in": name_tags}}, {"user_id": {"$in": all_user_refs}}]
    }).to_list(5000)
    delta_by_menu: dict[str, int] = {}
    for t in menu_txs:
        mid = t.get("menu_id")
        if not mid:
            continue
        qty = int(t.get("qty") or 0)
        sign = 1 if t.get("type") == "produce" else -1
        delta_by_menu[mid] = delta_by_menu.get(mid, 0) + sign * qty
    print(f"\nReversing menu stock on {len(delta_by_menu)} menus:")
    for mid, delta in delta_by_menu.items():
        if delta == 0:
            continue
        m = await db.menus.find_one({"id": mid})
        if not m:
            continue
        cur = int(m.get("stock") or 0)
        new = max(0, cur - delta)
        print(f"  {m.get('name')}: {cur} - {delta} -> {new}")
        if not dry_run:
            await db.menus.update_one({"id": mid}, {"$set": {"stock": new}})

    # --- 3) Delete transactional data created by dummies -------------------
    deletions = [
        ("sessions", {"user_id": {"$in": all_user_refs}}),
        ("login_attempts", {"$or": [{"username": {"$in": usernames}}, {"user_id": {"$in": all_user_refs}}]}),
        ("audit_logs", {"user_id": {"$in": all_user_refs}}),
        ("attendance", {"$or": [{"user_id": {"$in": all_user_refs}}, {"rider_id": {"$in": all_user_refs}}]}),
        ("gps", {"$or": [{"user_id": {"$in": all_user_refs}}, {"rider_id": {"$in": all_user_refs}}]}),
        ("sales", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"rider_name": {"$in": names}}, {"created_by": {"$in": all_user_refs}}]}),
        ("rider_stock", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"created_by": {"$in": all_user_refs}}, {"pic_id": {"$in": all_user_refs}}, {"rider_name": {"$in": names}}, {"pic_name": {"$in": names}}, {"verified_by": {"$in": all_user_refs}}]}),
        ("eod", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"rider_name": {"$in": names}}, {"created_by": {"$in": all_user_refs}}]}),
        ("deposits", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"rider_name": {"$in": names}}, {"created_by": {"$in": all_user_refs}}, {"user_id": {"$in": all_user_refs}}]}),
        ("handovers", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"created_by": {"$in": all_user_refs}}, {"from_id": {"$in": all_user_refs}}, {"to_id": {"$in": all_user_refs}}]}),
        ("rank_resets", {"rider_id": {"$in": all_user_refs}}),
        ("withdrawals", {"$or": [{"rider_id": {"$in": all_user_refs}}, {"user_id": {"$in": all_user_refs}}]}),
        ("expenses", {"$or": [{"created_by": {"$in": all_user_refs}}, {"user_id": {"$in": all_user_refs}}, {"created_by_name": {"$in": names}}]}),
        ("purchase_orders", {"$or": [{"created_by": {"$in": all_user_refs}}, {"requested_by": {"$in": all_user_refs}}, {"approved_by": {"$in": all_user_refs}}, {"received_by": {"$in": all_user_refs}}, {"created_by_name": {"$in": names}}]}),
        ("invoices", {"$or": [{"created_by": {"$in": all_user_refs}}, {"user_id": {"$in": all_user_refs}}]}),
        ("po_share_audit", {"user_id": {"$in": all_user_refs}}),
        ("inventory_tx", {"$or": [{"user": {"$in": name_tags}}, {"user_id": {"$in": all_user_refs}}]}),
        ("menu_stock_tx", {"$or": [{"user": {"$in": name_tags}}, {"user_id": {"$in": all_user_refs}}]}),
        ("notifications", {"$or": [{"user_id": {"$in": all_user_refs}}, {"to_user_id": {"$in": all_user_refs}}, {"from_user_id": {"$in": all_user_refs}}]}),
        ("coach_chats", {"user_id": {"$in": all_user_refs}}),
        ("coach_sessions", {"user_id": {"$in": all_user_refs}}),
    ]
    print("\nDeleting dummy-created records:")
    total = 0
    for col, q in deletions:
        n = await db[col].count_documents(q)
        if n > 0:
            print(f"  {col}: {n}")
            if not dry_run:
                res = await db[col].delete_many(q)
                total += res.deleted_count

    # --- 4) Finally delete the dummy users ---------------------------------
    print(f"\nDeleting {len(dummies)} dummy user docs...")
    if not dry_run:
        res = await db.users.delete_many({"_id": {"$in": obj_ids}})
        print(f"  deleted {res.deleted_count} users")

    print(f"\nTotal transactional docs deleted: {total}")
    print("Done." if not dry_run else "Dry-run complete.")


if __name__ == "__main__":
    asyncio.run(main("--dry" in sys.argv))
