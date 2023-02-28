import os
def list_files(filepath, filetype):
   paths = []
   for root, dirs, files in os.walk(filepath):
      for file in files:
         if file.lower().endswith(filetype.lower()):
            paths.append(os.path.join(root, file))
   return(paths)

paths = list_files('extraction/pass', '.jpg')

path_selection = {}

for path in paths:
    if 'field_name=preferences' in path:
        path_selection['preferences'] = path
    elif 'field_name=instructions' in path:
        path_selection['instructions'] = path

print(path_selection)
