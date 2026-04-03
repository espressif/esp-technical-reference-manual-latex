import argparse
import subprocess
import os
import glob
import shutil

def modify_font_in_preamble(font_config_path):
    with open(font_config_path, 'r') as file:
        content = file.readlines()

    # Replace Maison with Helvetica
    new_content = [
        line.replace('{MaisonNeue}', '{HelveticaNeue}')
            .replace('-LightItalic', 'LTPro-ThIt')
            .replace('MaisonNeueMono-Regular.otf', 'Menlo.ttc')
        for line in content
    ]

    with open(font_config_path, 'w') as file:
        file.writelines(new_content)

def build_single_pdf(chip_series, module_names, languages, suffix="", output_dir="out"):
    build_cmd = [
        'latexmk',
        '-pdf',
        # When ``-f`` is used, latexmk will continue building
        # if it encounters errors. We still receive a failure exit code
        # in this case, but the correct steps should run.
        '-f',
        '-dvi-',    # Don't generate dvi
        '-ps-',     # Don't generate ps
        '-interaction=nonstopmode',
        '-quiet',
        f'-output-directory={output_dir}',
        '-cd',      # Change to the directory where the build file is located
        ]

    # Extract the module name from the file name
    module_name = module_names.split('__')[-1]
    file_path_tex = glob.glob(f"{chip_series}/*{module_names}__{languages}.tex")[0]
    file_path_pdf = file_path_tex.replace(chip_series, f"{chip_series}/{output_dir}", 1).replace('.tex', f'{suffix}.pdf')
    file_path_log = file_path_pdf.replace('.pdf', '.log')

    # Export DOCUMENT_PATH as an environment variable
    with open("doc_path.env", "a") as env_file:
        env_file.write(f"DOCUMENT_PATH={file_path_pdf}\n")

    print(f'Building PDF from {file_path_tex}')
    if not os.path.exists(file_path_tex):
        exit(f'Input file {file_path_tex} does not exist!')

    subprocess.run(build_cmd + [file_path_tex], cwd='.')
    # Rename the additional PDF and log to include the suffix
    for path in [file_path_pdf, file_path_log]:
        original_path = path.replace(suffix, '')
        if os.path.exists(original_path):
            shutil.move(original_path, path)
    if not os.path.exists(file_path_pdf):
        exit(f'Output file {file_path_pdf} has not been built!')

def build_pdf(chip_series, module_names, languages):
    # Load RELEASE_LABEL from labels.env
    release_label = False
    if os.path.exists("labels.env"):
        with open("labels.env", "r") as env_file:
            release_label = any(line.startswith("RELEASE_LABEL=True") for line in env_file)

    preamble_path = './00-shared/config/preamble-shared.sty'

    # Back up the original preamble file
    backup_preamble = preamble_path + '.backup'
    shutil.copyfile(preamble_path, backup_preamble)

    try:
        # Build the standard PDF with the original preamble
        print(f"Building standard PDF: {chip_series}-{module_names}__{languages}.pdf")
        build_single_pdf(chip_series, module_names, languages)

        # If release_label is True, build the additional PDF with the modified preamble
        if release_label:
            print(f"Modifying preamble at {preamble_path}")
            modify_font_in_preamble(preamble_path)
            print(f"Building additional PDF: {chip_series}-{module_names}__{languages}-additional.pdf")
            build_single_pdf(chip_series, module_names, languages, suffix="-additional", output_dir="out/additional")
    finally:
        # Restore the original preamble file
        shutil.move(backup_preamble, preamble_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build PDFs')
    parser.add_argument('-c', '--chip_series', type=str, help='Chip series')
    parser.add_argument('-m', '--module_names', type=str, help='Module names')
    parser.add_argument('-l', '--languages', type=str, help='Languages')

    args = parser.parse_args()

    if args.chip_series and args.module_names and args.languages:
        build_pdf(args.chip_series, args.module_names, args.languages)
