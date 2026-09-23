import os
import zipfile

addon_dir = "addon"
output_name = "ricerca_testuale_accesso_digitale-1.5.1.nvda-addon"
skip_dirs = {"__pycache__"}

print(f"Creazione del pacchetto NVDA per la versione 1.5.1...")

with zipfile.ZipFile(output_name, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(addon_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith(".pyc"):
                continue
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, addon_dir)
            zipf.write(full_path, arcname)
            print(f"Aggiunto: {arcname}")

print(f"\nPacchetto completato con successo: {output_name}")