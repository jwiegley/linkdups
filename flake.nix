{
  description = "linkdups - Find and hard-link duplicate files to save disk space";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;

        linkdups = python.pkgs.buildPythonApplication {
          pname = "linkdups";
          version = "2.0.0";
          src = self;
          pyproject = true;

          build-system = [ python.pkgs.hatchling ];
          dependencies = [ ];

          nativeCheckInputs = with python.pkgs; [
            pytestCheckHook
            pytest-cov
            hypothesis
          ];

          pytestFlagsArray = [
            "tests/"
            "-x"
            "-q"
            "--ignore=tests/test_benchmark.py"
          ];
        };

        devPython = python.withPackages (
          ps: with ps; [
            pytest
            pytest-cov
            pytest-benchmark
            hypothesis
            mypy
          ]
        );
      in
      {
        packages.default = linkdups;

        devShells.default = pkgs.mkShell {
          packages = [
            devPython
            pkgs.ruff
            pkgs.lefthook
          ];

          shellHook = ''
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

        checks = {
          inherit linkdups;

          format = pkgs.runCommand "check-format" { nativeBuildInputs = [ pkgs.ruff ]; } ''
            cd ${self}
            RUFF_CACHE_DIR=$TMPDIR/.ruff_cache ruff format --check src/ tests/ scripts/
            touch $out
          '';

          lint = pkgs.runCommand "check-lint" { nativeBuildInputs = [ pkgs.ruff ]; } ''
            cd ${self}
            RUFF_CACHE_DIR=$TMPDIR/.ruff_cache ruff check src/ tests/ scripts/
            touch $out
          '';

          typecheck = pkgs.runCommand "check-typecheck" { nativeBuildInputs = [ devPython ]; } ''
            cd ${self}
            MYPYPATH=src MYPY_CACHE_DIR=$TMPDIR/.mypy_cache mypy src/linkdups/
            touch $out
          '';

          tests = pkgs.runCommand "check-tests" { nativeBuildInputs = [ devPython ]; } ''
            cp -r ${self}/src ${self}/tests ${self}/pyproject.toml .
            chmod -R u+w .
            HOME=$TMPDIR PYTHONPATH=src:$PYTHONPATH \
              python -m pytest tests/ -x -q \
                --ignore=tests/test_benchmark.py \
                --cov=linkdups --cov-report=term-missing --cov-fail-under=80
            touch $out
          '';
        };
      }
    );
}
