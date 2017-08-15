from conans import ConanFile, CMake, tools, ConfigureEnvironment
import os
import shutil


class ProtobufConan(ConanFile):
    name = "Protobuf"
    version = "3.3.0"
    url = "https://github.com/memsharded/conan-protobuf.git"
    license = "https://github.com/google/protobuf/blob/v3.3.0/LICENSE"
    requires = "zlib/1.2.8@lasote/stable"
    settings = "os", "compiler", "build_type", "arch"
    exports = "CMakeLists.txt", "lib*.cmake", "extract_includes.bat.in", "protoc.cmake", "tests.cmake", "change_dylib_names.sh"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=True", "fPIC=False"
    generators = "cmake"

    def config(self):
        self.options["zlib"].shared = self.options.shared

    def source(self):
        tools.download("https://github.com/google/protobuf/"
                       "releases/download/v3.3.0/protobuf-3.3.0.zip",
                       "protobuf.zip")
        tools.unzip("protobuf.zip")
        os.unlink("protobuf.zip")
        os.makedirs("protobuf-3.3.0/cmake")
        shutil.move("CMakeLists.txt", "protobuf-3.3.0/cmake")
        shutil.move("libprotobuf.cmake", "protobuf-3.3.0/cmake")
        shutil.move("libprotobuf-lite.cmake", "protobuf-3.3.0/cmake")
        shutil.move("libprotoc.cmake", "protobuf-3.3.0/cmake")
        shutil.move("protoc.cmake", "protobuf-3.3.0/cmake")
        shutil.move("tests.cmake", "protobuf-3.3.0/cmake")
        shutil.move("extract_includes.bat.in", "protobuf-3.3.0/cmake")
        shutil.move("change_dylib_names.sh", "protobuf-3.3.0/cmake")

    def build(self):
        if self.settings.os == "Windows":
            args = ['-DBUILD_TESTING=OFF']
            args += ['-DBUILD_SHARED_LIBS=%s' % ('ON' if self.options.shared else 'OFF')]
            cmake = CMake(self.settings)
            self.run('cd protobuf-3.3.0/cmake && cmake . %s %s' % (cmake.command_line, ' '.join(args)))
            self.run("cd protobuf-3.3.0/cmake && cmake --build . %s" % cmake.build_config)
        else:
            env = ConfigureEnvironment(self)
            cpus = tools.cpu_count()

            self.run("chmod +x protobuf-3.3.0/autogen.sh")
            self.run("chmod +x protobuf-3.3.0/configure")
            self.run("cd protobuf-3.3.0 && ./autogen.sh")

            args = []
            if not self.options.shared:
                args += ['--disable-shared']
            
            if self.options.shared or self.options.fPIC:
                args += ['"CFLAGS=-fPIC" "CXXFLAGS=-fPIC"']

            self.run("cd protobuf-3.3.0 && %s ./configure %s" % (env.command_line, ' '.join(args)))
            self.run("cd protobuf-3.3.0 && make -j %s" % cpus)

    def package(self):
        self.copy_headers("*.h", "protobuf-3.3.0/src")
        self.copy("descriptor.proto", "include/google/protobuf", "protobuf-3.3.0/src/google/protobuf", keep_path=False)
        self.copy("plugin.proto", "include/google/protobuf/compiler", "protobuf-3.3.0/src/google/protobuf/compiler", keep_path=False)

        if self.settings.os == "Windows":
            self.copy("*.lib", "lib", "protobuf-3.3.0/cmake", keep_path=False)
            self.copy("protoc.exe", "bin", "protobuf-3.3.0/cmake/bin", keep_path=False)

            if self.options.shared:
                self.copy("*.dll", "bin", "protobuf-3.3.0/cmake/bin", keep_path=False)
        else:
            # Copy the libs to lib
            if not self.options.shared:
                self.copy("*.a", "lib", "protobuf-3.3.0/src/.libs", keep_path=False)
            else:
                self.copy("*.so*", "lib", "protobuf-3.3.0/src/.libs", keep_path=False, symlinks=True)
                self.copy("*.9.dylib", "lib", "protobuf-3.3.0/src/.libs", keep_path=False, symlinks=True)

            # Copy the exe to bin
            if self.settings.os == "Macos":
                if not self.options.shared:
                    self.copy("protoc", "bin", "protobuf-3.3.0/src/", keep_path=False)
                else:
                    # "protoc" has libproto*.dylib dependencies with absolute file paths.
                    # Change them to be relative.
                    self.run("cd protobuf-3.3.0/src/.libs && bash ../../cmake/change_dylib_names.sh")

                    # "src/protoc" may be a wrapper shell script which execute "src/.libs/protoc".
                    # Copy "src/.libs/protoc" instead of "src/protoc"
                    self.copy("protoc", "bin", "protobuf-3.3.0/src/.libs/", keep_path=False)
                    self.copy("*.9.dylib", "bin", "protobuf-3.3.0/src/.libs", keep_path=False, symlinks=True)
            else:
                self.copy("protoc", "bin", "protobuf-3.3.0/src/", keep_path=False)

    def package_info(self):
        if self.settings.os == "Windows":
            self.cpp_info.libs = ["libprotobuf"]
            if self.options.shared:
                self.cpp_info.defines = ["PROTOBUF_USE_DLLS"]
        elif self.settings.os == "Macos":
            self.cpp_info.libs = ["libprotobuf.a"] if not self.options.shared else ["libprotobuf.9.dylib"]
        else:
            self.cpp_info.libs = ["protobuf"]