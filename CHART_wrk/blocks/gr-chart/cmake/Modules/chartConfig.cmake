INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_CHART chart)

FIND_PATH(
    CHART_INCLUDE_DIRS
    NAMES chart/api.h
    HINTS $ENV{CHART_DIR}/include
        ${PC_CHART_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    CHART_LIBRARIES
    NAMES gnuradio-chart
    HINTS $ENV{CHART_DIR}/lib
        ${PC_CHART_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(CHART DEFAULT_MSG CHART_LIBRARIES CHART_INCLUDE_DIRS)
MARK_AS_ADVANCED(CHART_LIBRARIES CHART_INCLUDE_DIRS)

