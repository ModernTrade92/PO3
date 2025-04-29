{ pkgs }: {
  deps = [
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.tesseract
    pkgs.poppler_utils
  ];
}