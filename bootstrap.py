"""Script que verifica/instala requerimientos ANTES de importar módulos."""

import glob
import os
import re
import sys
import platform
import subprocess


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def get_pip_exe() -> str:
    scripts_dir = os.path.dirname(sys.executable)
    if platform.system() == "Windows":
        return os.path.join(scripts_dir, "pip.exe")
    return os.path.join(scripts_dir, "pip")


def get_site_packages() -> str:
    import sysconfig

    return sysconfig.get_path("purelib")


def get_installed_packages() -> dict:
    """Lee paquetes directamente de los METADATA de cada .dist-info."""
    site_packages = get_site_packages()
    packages = {}
    matches = glob.glob(os.path.join(site_packages, "*.dist-info"))
    print(f"[DEBUG] site-packages: {site_packages}")
    print(f"[DEBUG] .dist-info encontrados: {len(matches)}")
    for dist_info in matches:
        metadata_file = os.path.join(dist_info, "METADATA")
        if not os.path.exists(metadata_file):
            continue
        name = version = None
        try:
            with open(metadata_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("Name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                    if name and version:
                        break
        except OSError:
            continue
        if name and version:
            packages[normalize_name(name)] = version
    print(f"[DEBUG] Paquetes leídos: {len(packages)}")
    return packages


def parse_requirements(requirements_path: str) -> list[str]:
    packages = []
    with open(requirements_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                packages.append(line)
    return packages


def packages_match_requirements(requirements_path: str) -> bool:
    from packaging.specifiers import SpecifierSet

    installed = get_installed_packages()
    mismatches = []

    for req in parse_requirements(requirements_path):
        # Extraer solo el nombre: separar extras [job-queue] y versión ==1.0
        name_part = req.split("[")[0].strip()
        for op in ("==", ">=", "<=", "!=", "~=", ">", "<"):
            if op in name_part:
                name_part = name_part[: name_part.index(op)].strip()
                break

        spec_str = ""
        for op in ("==", ">=", "<=", "!=", "~=", ">", "<"):
            if op in req:
                spec_str = req[req.index(op) :]
                break

        name = normalize_name(name_part)

        if name not in installed:
            mismatches.append(f"{req} (no instalado)")
            continue

        if spec_str:
            try:
                if not SpecifierSet(spec_str).contains(
                    installed[name], prereleases=True
                ):
                    mismatches.append(f"{req} (instalado: {installed[name]})")
            except Exception:
                pass

    if mismatches:
        print("Diferencias encontradas con requirements.txt:")
        for m in mismatches:
            print(f"  - {m}")
        return False
    return True


def install_requirements(requirements_path: str) -> None:
    print("Instalando requerimientos...\n")
    result = subprocess.run(
        [get_pip_exe(), "install", "-r", requirements_path],
        check=False,
    )
    if result.returncode != 0:
        print("\n✗ Error durante la instalación")
        sys.exit(1)
    print("\n✓ Requerimientos instalados correctamente\n")


def check_and_install_requirements() -> None:
    requirements_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "requirements.txt"
    )

    if not os.path.exists(requirements_path):
        print(f"✗ No se encontró {requirements_path}")
        sys.exit(1)

    if packages_match_requirements(requirements_path):
        return

    response = input("\nDescargar requerimientos (y/n): ").strip().lower()
    while response not in ("y", "n"):
        response = input("Opción inválida. Ingresa 'y' o 'n': ").strip().lower()

    if response == "y":
        install_requirements(requirements_path)
    else:
        print("Continuando sin instalar requerimientos...\n")


if __name__ == "__main__":
    check_and_install_requirements()

    from src.main import main

    main()


def check_and_install_requirements() -> None:
    """Comprueba si los requerimientos están al día y pregunta si instalarlos."""
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")

    if not os.path.exists(requirements_path):
        print(f"✗ Error: No se encontró {requirements_path}")
        sys.exit(1)

    if packages_match_requirements(requirements_path):
        return  # Todo ok, continuar sin preguntar

    response = input("\nDescargar requerimientos (y/n): ").strip().lower()
    while response not in ("y", "n"):
        response = (
            input("Opción inválida. Por favor ingresa 'y' o 'n': ").strip().lower()
        )

    if response == "y":
        install_requirements(requirements_path)
    else:
        print("Continuando sin instalar requerimientos...\n")


if __name__ == "__main__":
    check_and_install_requirements()

    from src.main import main

    main()
