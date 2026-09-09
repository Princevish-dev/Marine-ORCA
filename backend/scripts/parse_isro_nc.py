import os
import glob
import pandas as pd
import numpy as np
import h5netcdf

def process_isro_data(base_dir="D:/HackaThon SIH", output_dir="D:/HackaThon SIH/orca/backend/data/isro"):
    os.makedirs(output_dir, exist_ok=True)
    
    chl_files = glob.glob(os.path.join(base_dir, "*_STGOCLHND_*", "BAND.nc"))
    sst_files = glob.glob(os.path.join(base_dir, "*_STGOTSHND_*", "BAND.nc"))
    
    # 1. Process Chlorophyll
    chl_records = []
    print(f"Found {len(chl_files)} Chlorophyll files.")
    for f in chl_files:
        print(f"Parsing {f}...")
        try:
            with h5netcdf.File(f, 'r') as ds:
                lat = ds.variables['latitude'][:]
                lon = ds.variables['longitude'][:]
                cl_a = ds.variables['CL-a'][:]
                
                # Downsample by taking every 20th pixel to avoid massive CSVs
                step = 20
                lat_idx, lon_idx = np.where(~np.isnan(cl_a[::step, ::step]))
                
                for i, j in zip(lat_idx, lon_idx):
                    actual_i, actual_j = i * step, j * step
                    val = cl_a[actual_i, actual_j]
                    if val > 0:  # Valid chlorophyll
                        chl_records.append({
                            "latitude": round(float(lat[actual_i]), 4),
                            "longitude": round(float(lon[actual_j]), 4),
                            "chlorophyll_mgm3": round(float(val), 4)
                        })
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            
    if chl_records:
        df_chl = pd.DataFrame(chl_records)
        df_chl.to_csv(os.path.join(output_dir, "chlorophyll_grid.csv"), index=False)
        print(f"Saved {len(df_chl)} chlorophyll records.")

    # 2. Process SST
    sst_records = []
    print(f"Found {len(sst_files)} SST files.")
    for f in sst_files:
        print(f"Parsing {f}...")
        try:
            with h5netcdf.File(f, 'r') as ds:
                lat = ds.variables['latitude'][:]
                lon = ds.variables['longitude'][:]
                tsm = ds.variables['TSM'][:]
                
                step = 20
                lat_idx, lon_idx = np.where(~np.isnan(tsm[::step, ::step]))
                
                for i, j in zip(lat_idx, lon_idx):
                    actual_i, actual_j = i * step, j * step
                    val = tsm[actual_i, actual_j]
                    if val > 0:  # Valid SST
                        sst_records.append({
                            "latitude": round(float(lat[actual_i]), 4),
                            "longitude": round(float(lon[actual_j]), 4),
                            "sst_celsius": round(float(val), 2)
                        })
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            
    if sst_records:
        df_sst = pd.DataFrame(sst_records)
        df_sst.to_csv(os.path.join(output_dir, "sst_grid.csv"), index=False)
        print(f"Saved {len(df_sst)} SST records.")

if __name__ == "__main__":
    process_isro_data()
