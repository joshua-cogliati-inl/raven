
#ifndef PYTHONFMU_PYTHONSTATE_HPP
#define PYTHONFMU_PYTHONSTATE_HPP

#include <Python.h>
#include <iostream>
#ifdef __linux__
#include <dlfcn.h>
#endif

namespace pythonfmu
{

class PyState
{
public:
    PyState()
    {
        was_initialized_ = Py_IsInitialized();

        if (!was_initialized_) {
            Py_SetProgramName(L"./PythonFMU");
            Py_Initialize();
#ifdef __linux__
            //On linux, we need to load the python library
            // with dlopen and global to get all the python
            // symbols.
            PyObject * apiflags = PySys_GetObject("abiflags");
            if (PyUnicode_Check(apiflags)) {
                wchar_t apiflags_w[16];
                PyUnicode_AsWideChar(apiflags, apiflags_w, 16);
                apiflags_w[16-1] = '\0';
                char library[256];
                snprintf(library, 256, "libpython%d.%d%ls.so", PY_MAJOR_VERSION, PY_MINOR_VERSION, apiflags_w);
                library[256-1] = '\0';
                //printf("python library: %s\n", library);
                dlopen(library, RTLD_NOW | RTLD_GLOBAL);
            }
#endif
            PyEval_InitThreads();
            _mainPyThread = PyEval_SaveThread();
        }
    }

    ~PyState()
    {
        if (!was_initialized_) {
            PyEval_RestoreThread(_mainPyThread);
            Py_Finalize();
        }
    }

private:
    bool was_initialized_;
    PyThreadState* _mainPyThread;
};

} // namespace pythonfmu

#endif //PYTHONFMU_PYTHONSTATE_HPP
