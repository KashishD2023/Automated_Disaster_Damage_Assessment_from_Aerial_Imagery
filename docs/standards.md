## Project Standards

### Damage classes
No damage  
Minor damage  
Major damage  
Destroyed  

### Prediction output schema (GeoJSON properties)
tile_id  
damage_class  
confidence  
explanation  
pre_image_path  
post_image_path  

### Coordinate system
WGS84 latitude longitude (EPSG:4326)

### Tile ID rule
tile_id must be unique and consistent across tiles csv, predictions, and evaluation joins.
