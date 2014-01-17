import os
import sys
import shutil, errno

# def copyanything(src, dst):
#     try:
#         shutil.copytree(src, dst)
#     except OSError as exc:
#         if exc.errno == errno.ENOTDIR:
#             shutil.copy(src, dst)
#         else: raise

def copyanything(src, dst):
    if os.path.isfile(src):
        shutil.copy(src, dst)
    elif os.path.isdir(src):
        try:
            os.mkdir(dst)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else: raise
        for content in os.listdir(src):
            copyanything(os.path.join(src, content), os.path.join(dst, content))
    else:
        shutil.copy(src, dst)

copyanything(sys.argv[1], sys.argv[2])
