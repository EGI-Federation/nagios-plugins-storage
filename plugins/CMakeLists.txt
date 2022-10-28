cmake_minimum_required(VERSION 2.8)

file (GLOB storage_probe *.py)

install (FILES ${storage_probe}
         DESTINATION usr/lib${LIB_SUFFIX}/nagios/plugins/storage/
         PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ
                     GROUP_EXECUTE GROUP_READ
                     WORLD_EXECUTE WORLD_READ
)

