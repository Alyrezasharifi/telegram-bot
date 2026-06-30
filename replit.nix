{ pkgs }: {
  deps = [
    pkgs.python313
    pkgs.python313Packages.pip
  ];
  env = {
    PYTHONUNBUFFERED = "1";
  };
}
