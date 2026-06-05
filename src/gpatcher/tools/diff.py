import detools

def invoke_hdiffz(old_file: str, new_file: str, patch_out: str):
    with open(old_file, 'rb') as old_f, \
         open(new_file, 'rb') as new_f, \
         open(patch_out, 'wb') as patch_f:
        detools.create_patch(old_f, new_f, patch_f, algorithm='hdiffpatch')

def invoke_hpatchz(old_file:str, patch_file: str, new_out: str):
    with open(old_file, 'rb') as old_f, \
         open(patch_file, 'rb') as patch_f, \
         open(new_out, 'wb') as new_f:
        detools.apply_patch(old_f, patch_f, new_f)