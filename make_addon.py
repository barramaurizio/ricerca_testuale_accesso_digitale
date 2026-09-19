import os
import zipfile

addon_dir = "addon"
output_name = "ricerca_testuale_accesso_digitale-1.4.5.nvda-addon"

print(f"Creazione del pacchetto NVDA per la versione 1.4.5...")

with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(addon_dir):
        for file in files:
            full_path = os.path.join(root, file)
            # Calcola il percorso relativo per mantenere la struttura corretta dentro l'archivio
            arcname = os.path.relpath(full_path, addon_dir)
            zipf.write(full_path, arcname)
            print(f"Aggiunto: {arcname}")

print(f"\nPacchetto completato con successo: {output_name}")