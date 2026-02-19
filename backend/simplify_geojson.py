import json
import os
import math

def simplify_points(coordinates, tolerance=0.0001):
    """
    Simplifies a list of coordinates using a simple distance-based optimization 
    (similar to a simplified Visvalingam-Wyatt or RDP).
    tolerance: minimum distance between points to keep them (in degrees).
    """
    if not coordinates:
        return []
    
    simplified = [coordinates[0]]
    last_point = coordinates[0]
    
    for point in coordinates[1:-1]:
        # Calculate squared distance to avoid sqrt performance hit
        dist_sq = (point[0] - last_point[0])**2 + (point[1] - last_point[1])**2
        if dist_sq > tolerance**2:
            simplified.append(point)
            last_point = point
            
    simplified.append(coordinates[-1])
    return simplified

def process_geometry(geometry):
    if geometry['type'] == 'Polygon':
        new_coords = []
        for ring in geometry['coordinates']:
            new_coords.append(simplify_points(ring, tolerance=0.001)) # Approx 100m precision
        geometry['coordinates'] = new_coords
    elif geometry['type'] == 'MultiPolygon':
        new_coords = []
        for polygon in geometry['coordinates']:
            new_poly = []
            for ring in polygon:
                new_poly.append(simplify_points(ring, tolerance=0.001))
            new_coords.append(new_poly)
        geometry['coordinates'] = new_coords
    return geometry

def main():
    input_path = 'frontend/data/data-comuni.original.js'
    output_path = 'frontend/data/data-comuni.js'
    
    print(f"Reading from {input_path}...")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Strip JS variable declaration to get JSON
    json_str = content.replace('const comuniData =', '').strip()
    if json_str.endswith(';'):
        json_str = json_str[:-1]
        
    data = json.loads(json_str)
    
    print(f"Original features: {len(data['features'])}")
    
    # Process
    for feature in data['features']:
        if 'geometry' in feature and feature['geometry']:
            feature['geometry'] = process_geometry(feature['geometry'])
            
    # Round coordinates to 4 decimal places (approx 10m precision) to save space
    # This is done during serialization strictly implicitly by python's float handling usually, 
    # but we can force it if needed. For now the simplification removes points which is the main factor.
            
    print("Writing simplified data...")
    
    # Convert back to JS 
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('const comuniData = ')
        json.dump(data, f, separators=(',', ':')) # Minimal separators
        f.write(';')
        
    original_size = os.path.getsize(input_path) / (1024*1024)
    new_size = os.path.getsize(output_path) / (1024*1024)
    
    print(f"Done! Reduced from {original_size:.2f} MB to {new_size:.2f} MB")

if __name__ == "__main__":
    main()
