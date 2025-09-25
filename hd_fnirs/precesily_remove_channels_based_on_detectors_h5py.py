
import h5py

import numpy as np
import os


raw_data_folder = "C:/nirs/hd_fnirs/raw_data/"

sparse_folder = "C:/nirs/hd_fnirs/sparse/"

# Walk through the raw data directory
for dirpath, dirnames, filenames in os.walk(raw_data_folder):
    # Construct the corresponding path in the destination directory
    # os.path.relpath gets the path relative to the raw_data_folder
    relative_path = os.path.relpath(dirpath, raw_data_folder)
    destination_path = os.path.join(sparse_folder, relative_path)
    
    # Create the directory in the destination if it doesn't exist
    os.makedirs(destination_path, exist_ok=True)
    
    print(f"Checking directory: {dirpath}")
    
    # Process and copy the .snirf files
    for filename in filenames:
        if filename.endswith(".snirf"):
            source_filepath = os.path.join(dirpath, filename)
            
            # Load the data
            hd = h5py.File(source_filepath, 'r')
            
            
            new_filename = filename.replace(".snirf", "_sparse.snirf")
            destination_filepath = os.path.join(destination_path, new_filename)
            
            
            # Copy File
            with h5py.File(destination_filepath, 'w') as dest_hd:
                # Copy all groups and datasets from the source to the destination
                for name, item in hd.items():
                    hd.copy(item, dest_hd, name)
            print("Copied ", filename," file to : ", destination_filepath)
            
            modified = h5py.File(destination_filepath, 'r+')
               
            probe = modified["nirs"]["probe"]
            detector_pos_2d = probe["detectorPos2D"]
            detector_pos_3d = probe["detectorPos3D"]
            
            # Cache the dataset
            d_2d = detector_pos_2d[()]
            d_3d = detector_pos_3d[()]
            
            del probe["detectorPos2D"] # Delete the old dataset
            del probe["detectorPos3D"]
            
            # Replace with only the first 4 detectors
            modified["nirs"]["probe"]["detectorPos2D"] = d_2d[0:4] # Keep only first 4 detectors
            modified["nirs"]["probe"]["detectorPos3D"] = d_3d[0:4]
            
            # Now we need to remove the channels that are not in the sparse set
            nirs = modified["nirs"]
            for name, item in nirs.items():
                print(f"NIRS - {name}: {item}")

            data1 = nirs["data1"]
            for name in data1:
                print(f"DATA1 - {name}: {item}")

            channel_indices_to_keep = []


            for name, item in data1.items():
                if "measurementList" not in name:
                    continue
                
                # CHeck if the name contains "measurementList" -> Then proceed here
                sourceIndex = data1[name]["sourceIndex"][()]
                detectorIndex = data1[name]["detectorIndex"][()]
                wavelength = data1[name]["wavelengthIndex"][()]

                #print(f"{name} - {sourceIndex}, {detectorIndex}, {wavelength}")

                if detectorIndex in [1,2,3,4]: # Only keep detectors 1,2,3,4
                    print(f"KEEP {name} - {sourceIndex}, {detectorIndex}, {wavelength}")
                    # Determine the timeseresData index to keep = 
                    channel_indices_to_keep.append(int(name.replace("measurementList", "")) - 1)
                    # We found the index to keep, now we somehow need to align these two soruces
                else:
                    print(f"REMOVE {name} - {sourceIndex}, {detectorIndex}, {wavelength}")
                    del data1[name] # Delete the entire measurementList entry

            measurement_keys = [
                name
                for name in data1.keys()
                if name.startswith("measurementList")
            ]

            # Sort based on the numerical part of the key
            sorted_keys = sorted(
                measurement_keys,
                key=lambda x: int(x.replace("measurementList", ""))
            )

            # 2. Rename elements in the file
            # To avoid conflicts, we'll use a temporary group to hold elements
            # while we rename them.

            # Create a temporary group to store the elements.
            temp_group_name = "__temp_renaming_group__"
            data1.create_group(temp_group_name)

            # Move all sorted elements into the temp group.
            for i, old_name in enumerate(sorted_keys):
                new_name_temp = f"measurementList_temp_{i}"
                data1.move(old_name, f"{temp_group_name}/{new_name_temp}")

            # Move them back with the new sequential names.
            for i in range(len(sorted_keys)):
                new_name_sequential = f"measurementList{i+1}"
                old_name_temp = f"measurementList_temp_{i}"
                data1.move(f"{temp_group_name}/{old_name_temp}", new_name_sequential)

            # Delete the temporary group.
            del data1[temp_group_name]
            print(f" AFTER REMOVING SHORT CHANNELS AND SORTING")
            for name, item in data1.items():
                print(f"DATA1 - {name}: {item}")


            time = np.array(data1["time"]) # No need to change
            print(f"Time shape: {time.shape}") # Should be (num_timepoints,

            old_channel_data = np.array(data1["dataTimeSeries"]).T
            print(f"Channel data shape: {old_channel_data.shape}") # Should be (num_channels, num_timepoints)

            new_channel_data = []
            for i, idx in enumerate(channel_indices_to_keep):
                new_channel_data.append(old_channel_data[idx])

            new_channel_data = np.array(new_channel_data).T

            del data1["dataTimeSeries"]
            data1["dataTimeSeries"] = new_channel_data # THis is now succesfully replaced

            modified.close()
            