cmake_minimum_required(VERSION 2.8)

file (GLOB xrootd_probe *.py)

install (FILES ${xrootd_probe}
         DESTINATION usr/lib${LIB_SUFFIX}/nagios/plugins/xrootd/
         PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ
                     GROUP_EXECUTE GROUP_READ
                     WORLD_EXECUTE WORLD_READ
)

