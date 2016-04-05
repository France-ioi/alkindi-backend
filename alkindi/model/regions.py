
def load_region(db, region_id, for_update=False):
    if region_id is None:
        return None
    keys = ['id', 'name', 'code']
    result = db.load_row(db.tables.regions, region_id, keys,
                         for_update=for_update)
    return result
