import argparse
import os
from core import EnZight
import sys
from utils import detect_format, download_AF_structure, validate_structure_file, encrypt_key, create_output_dirs, log_message, detect_structure_format, download_query_pdb
import shutil
import zipfile
import re

def main():

    # Generate a default job key
    job_key = encrypt_key()

    # Set up argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--QUERY",
        type=str,
        default=None,
        help="Path to the query protein structure file (.pdb or .cif)."
    )
    parser.add_argument(
        "--QUERY_ID",
        type=str,
        default=None,
        help="PDB or UniProt ID of the query protein."
    )
    parser.add_argument(
        "-hom",
        "--HOMOLOGS",
        nargs="+",
        default=None,
        help="List of paths to files used as homologs for the query file (only required for user-specified homology search method)."
    )  
    parser.add_argument(
        "-hom-id",
        "--HOMOLOGS_ID",
        type=str,
        default=None,
        help="PDB or UniProt IDs used as homologs, separated by spaces or commas."
    )
    parser.add_argument(
        "-hom-dir",
        "--HOMOLOGS_DIR",
        type=str,
        default=None,
        help="Folder with files used as homologs for the query file (only required for user-specified homology search method)."
    ) 
    parser.add_argument(
        "-j",
        "--JOB_KEY",
        type=str,
        default=job_key,
        help="The job key (job name). The generated files will be saved under this name."
    )
    parser.add_argument(
        "-H",
        "--HOMOLOGY_SEARCH_METHOD",
        type=str,
        default="foldseek",
        choices=['foldseek', 'user_specified'],
        help="Method used to fetch homologs for usage in the program. Choose either foldseek or user_specified. (default is foldseek)."
    )
    parser.add_argument(
        "-d",
        "--MAX_DISTANCE",
        type=int,
        default=5,
        help="Threshold distance for gap recognition. If an amino acid has more than this distance to the query structure, it is recognized as a gap."
    )
    parser.add_argument(
        "-r",
        "--MAX_RMSD",
        type=int,
        default=5,
        help="Max allowed RMSD ('Root-Mean-Square Deviation'). Structures aligning with a higher RMSD than the given threshold will be removed from the algorithm."
    )
    parser.add_argument(
        "-fd",
        "--FOLDSEEK_DATABASES",
        nargs="+",
        choices=["afdb50", "afdb_swissprot", "afdb_proteome", "pdb100"],
        default=[],
        help="Foldseek databases (only necessary for foldseek search method). Default: afdb50."
    )
    parser.add_argument(
        "--afdb50",
        action="store_true",
        help="Use afdb50 database for foldseek search method."
    )
    parser.add_argument(
        "--afdb_swissprot",
        action="store_true",
        help="Use afdb_swissprot database for foldseek search method."
    )
    parser.add_argument(
        "--afdb_proteome",
        action="store_true",
        help="Use afdb_proteome database for foldseek search method."
    )
    parser.add_argument(
        "--pdb100",
        action="store_true",
        help="Use pdb100 database for foldseek search method."
    )
    parser.add_argument(
        "-fm",
        "--FOLDSEEK_MODE",
        type=str,
        default="tmalign",
        choices=["tmalign", "3diaa"],
        help="Foldseek mode - Either 'TM-align' or '3Di/AA' (only necessary for foldseek search method). Default: tmalign."
    )
    parser.add_argument(
        "-ft",
        "--FOLDSEEK_THRESHOLD",
        type=float,
        default=0.7,
        help="Foldseek threshold (either TM or E-value threshold depending on Foldseek mode)."
    )
    parser.add_argument(
        "-nh",
        "--NUMB_HOMOLOGS",
        type=int,
        default=20,
        help="Number of top performing Foldseek homologs based on (TM or E-value depending on Foldseek mode) that is used in the EnZight algorithm."
    )

    parser.add_argument(
        "-R",
        "--RESULT_DIR",
        type=str,
        default=os.path.join(".", f"{job_key}"),
        help="The path to the result folder."
    )
    parser.add_argument(
        "-tmp",
        "--TMP_DIR",
        type=str,
        default=os.path.join(".", "tmp"),
        help="The path to the tmp folder."
    )   
    parser.add_argument(
        "-b",
        "--BLOSUM",
        type=str,
        default="BLOSUM62",
        choices=["BLOSUM50","BLOSUM62"],
        help="BLOSUM matrix used for sequence alignment."
    )
    parser.add_argument(
        "--only_core",
        type=str,
        default="1",
        choices=["0", "1"],
        help="If set to 1, only hotspots in the core of the protein will be considered. If set to 0, all hotspots will be considered. Default is 1."
    )

    args = parser.parse_args()

    # Query can either be an uploaded structure or a PDB/UniProt ID
    if args.QUERY:
        query_file = args.QUERY
    elif args.QUERY_ID:
        query_file = args.QUERY_ID.strip()
    else:
        parser.error("A query structure file or PDB/UniProt ID must be provided.")
        sys.exit(1)

    tmp_dir, result_dir = create_output_dirs(args.RESULT_DIR, args.TMP_DIR)



    if detect_format(query_file):
        string, format = detect_format(query_file)
        if format == "unknown":
            print(f'<p style="color:red;"><b>ERROR:</b> Could not detect structure format for query file ({query_file}). Please make sure the pdb or uniprot ID is valid.</p>')
            sys.exit(1)
        elif format == "PDBID":
            try:
                query_file = download_query_pdb(string,tmp_dir)
            except Exception as e:
                print(f'<p style="color:red;"><b>ERROR:</b> Could not download PDB structure for Query {string}. Please make sure the PDB ID is valid.</p>')
                sys.exit(1)
            # query_file = f"{query_file}.{format}"
            # print(query_file)
        elif format == "AF":
            try:
                query_file = download_AF_structure(string,tmp_dir,log_file_path=None)
            except Exception as e:
                print(f'<p style="color:red;"><b>ERROR:</b> Could not download AlphaFold structure for Query {string}. Please make sure the uniprot ID is valid.</p>')
                sys.exit(1)


        
    # Change "0" extension to ".pdb"/".cif" for web server
    elif query_file.endswith(".0"):
        old_query_path = query_file
        query_file = detect_structure_format(old_query_path)
        # args.QUERY = args.QUERY[:-1] + "pdb"
        new_query_path = query_file
        if new_query_path.endswith("0"):
            print(f'<p style="color:red;"><b>ERROR:</b> Could not detect structure format for query file ({old_query_path}). Please make sure the file has a valid structure format extension (.pdb or .cif).</p>')
            sys.exit(1)
        os.rename(old_query_path, new_query_path)
        # Validate arguments and inputs
        if not validate_structure_file(query_file):
            print(f'<p style="color:red;"><b>ERROR:</b> Could not open or read query file</p>')
            sys.exit(1)
    else:
        # Validate arguments and inputs
        if not validate_structure_file(query_file):
            print(f'<p style="color:red;"><b>ERROR:</b> Could not open or read query file</p>')
            sys.exit(1)

    if args.FOLDSEEK_DATABASES == []:
        if args.afdb50:
            args.FOLDSEEK_DATABASES.append("afdb50")
        if args.afdb_swissprot:
            args.FOLDSEEK_DATABASES.append("afdb_swissprot")
        if args.afdb_proteome:
            args.FOLDSEEK_DATABASES.append("afdb_proteome")
        if args.pdb100:
            args.FOLDSEEK_DATABASES.append("pdb100")
        if args.FOLDSEEK_DATABASES == []:
            args.FOLDSEEK_DATABASES = ["afdb50"]      




    if args.HOMOLOGY_SEARCH_METHOD == "user_specified":
        if args.HOMOLOGS is None and args.HOMOLOGS_DIR is None and args.HOMOLOGS_ID is None:
            print(f'<p style="color:red;"><b>ERROR:</b> Please provide either a list of homolog files / IDs or a directory containing homolog files when using user-specified homology search method.</p>')
            sys.exit(1)
        elif args.HOMOLOGS_DIR is None:
            if args.HOMOLOGS:
                homologs = args.HOMOLOGS

            elif args.HOMOLOGS_ID:
                homologs = [
                    x for x in re.split(r"[\s,]+", args.HOMOLOGS_ID.strip())
                    if x
                ]

            # homologs = homologs.copy()
            remove_indices = []
            for i, homolog in enumerate(homologs):
                if detect_format(homolog):
                    string, format = detect_format(homolog)
                    if format == "unknown":
                        print(f'<p style="color:orange;"><b>WARNING:</b> Could not detect structure format for homolog file ({homolog}). Please make sure the pdb or uniprot ID is valid.</p>')
                        remove_indices.append(i)
                    elif format == "PDBID":
                        homologs[i] = f"{homolog}.{format}"
                    elif format == "AF":
                        try:
                            homologs[i] = download_AF_structure(string,tmp_dir,log_file_path=None)
                        except Exception as e:
                            print(f'<p style="color:orange;"><b>WARNING:</b> Could not download AlphaFold structure for Query {string}. Please make sure the uniprot ID is valid.</p>')
                            remove_indices.append(i)
            for i in reversed(remove_indices):
                homologs.pop(i)
            
        else:
            homologs = [os.path.join(args.HOMOLOGS_DIR, hom_file) for hom_file in os.listdir(args.HOMOLOGS_DIR)]

        if len(homologs) == 0:
            print(
                '<p style="color:red;"><b>ERROR:</b> '
                'No valid homolog files provided. Please provide 2 or more homolog files '
                'when using user-specified homology search method.</p>'
            )
            sys.exit(1)

        # Zip file handling for web server
        elif len(homologs) == 1:
            zip_file_path = homologs[0]

            if zipfile.is_zipfile(zip_file_path):
                extract_dir = os.path.join(tmp_dir, f"{args.JOB_KEY}_homologs")
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                homologs = [
                    os.path.join(extract_dir, hom_file)
                    for hom_file in os.listdir(extract_dir)
                    if hom_file.lower().endswith((".pdb", ".cif"))
                ]

                if len(homologs) < 2:
                    print(
                        '<p style="color:red;"><b>ERROR:</b> '
                        'The zip file must contain at least 2 .pdb or .cif files.</p>'
                    )
                    sys.exit(1)

            elif zip_file_path.lower().endswith((".pdb", ".cif")):
                print(
                    '<p style="color:red;"><b>ERROR:</b> '
                    'Please provide 2 or more homolog files when using '
                    'user-specified homology search method.</p>'
                )
                sys.exit(1)

            else:
                print(
                    '<p style="color:red;"><b>ERROR:</b> '
                    'The provided homolog file is not a valid zip file.</p>'
                )
                sys.exit(1)


        # # Change "0" extension to ".pdb" for web server
        # for i, temp_file in enumerate(homologs):
        #     print(temp_file)
        #     if temp_file.endswith(".0"):
        #         old_temp_file_path = temp_file
        #         new_temp_file_path = detect_structure_format(old_temp_file_path)
        #         temp_file = new_temp_file_path
        #         print(f"Detected homolog file format for {old_temp_file_path}: {new_temp_file_path}")
        #         if new_temp_file_path.endswith("0"):
        #             homologs.pop(i)
        #             print(f'<p style="color:orange;"><b>WARNING:</b> Could not detect structure format for {old_temp_file_path}. This file will be skipped.</p>')
        #             continue
        #         # new_temp_file_path = temp_file
        #         os.rename(old_temp_file_path, new_temp_file_path)
        #         homologs[i] = new_temp_file_path
        #     if not validate_structure_file(temp_file):
        #         print(f'<p style="color:orange;"><b>WARNING:</b> Could not open or read {temp_file}</p>')
        #         homologs.remove(temp_file)
        # if len(homologs) < 2:
        #     print(f'<p style="color:red;"><b>ERROR:</b> After validating the homolog files, less than 2 valid homolog files remain. Please provide at least 2 valid homolog files.</p>')
        #     sys.exit(1)
    else:
        homologs = None


    if args.MAX_DISTANCE <= 0:
        print(f'<p style="color:red;"><b>ERROR:</b> The maximum sequence distance parameter (MAX_DISTANCE) must be greater than 0.</p>')
        sys.exit(1)

    if args.MAX_RMSD <= 0:
        print(f'<p style="color:red;"><b>ERROR:</b> The RMSD threshold (MAX_RMSD) must be greater than 0.</p>')
        sys.exit(1)

    if not (0.0 <= args.FOLDSEEK_THRESHOLD <= 1.0):
        print(f'<p style="color:red;"><b>ERROR:</b> The Foldseek threshold (FOLDSEEK_THRESHOLD) must be between 0.0 and 1.0.</p>')
        sys.exit(1)

    if args.NUMB_HOMOLOGS < 2:
        print(f'<p style="color:red;"><b>ERROR:</b> Please use 2 or more homolog files. NUMB_HOMOLOGS must be greater than 2.</p>')
        sys.exit(1)


    # Find MUSCLE binary
    muscle_path = shutil.which("muscle")
    if not muscle_path:
        print(f'<p style="color:red;"><b>ERROR:</b> MUSCLE binary not found on PATH</p>')
        sys.exit(1)

    
    zip_file_path = os.path.join(result_dir, f"{job_key}_EnZight")
    os.makedirs(zip_file_path, exist_ok=True)
    log_file_path = os.path.join(zip_file_path, f"{args.JOB_KEY}_log.txt")

    settings = [
        "EnZight run settings:",
        f"Query = {query_file}",
        f"job_key = {args.JOB_KEY}",
        f"result_dir = {args.RESULT_DIR}",
        f"tmp_dir = {args.TMP_DIR}",
        f"homologs = {homologs}",
        f"homology_search_method = {args.HOMOLOGY_SEARCH_METHOD}",
        f"max_dist = {args.MAX_DISTANCE}",
        f"max_rmsd = {args.MAX_RMSD}",
        f"foldseek_databases = {args.FOLDSEEK_DATABASES}",
        f"foldseek_mode = {args.FOLDSEEK_MODE}",
        f"foldseek_threshold = {args.FOLDSEEK_THRESHOLD}",
        f"numb_homologs = {args.NUMB_HOMOLOGS}",
        f"BLOSUM = {args.BLOSUM}",
        f"only_core = {args.only_core}",
        f"muscle_path = {muscle_path}",
        f"log_file_path = {log_file_path}"
    ]
    log_message(log_file_path, "\n".join(settings))



    # Run EnZight
    EnZight(query=query_file,
             job_key=args.JOB_KEY,
             result_dir=zip_file_path,
             tmp_dir=tmp_dir,
             homologs=homologs,
             homology_search_method=args.HOMOLOGY_SEARCH_METHOD,
             max_dist=args.MAX_DISTANCE,
             max_rmsd=args.MAX_RMSD,
             foldseek_databases=args.FOLDSEEK_DATABASES,
             foldseek_mode=args.FOLDSEEK_MODE,
             foldseek_threshold=args.FOLDSEEK_THRESHOLD,
             numb_homologs=args.NUMB_HOMOLOGS,
             BLOSUM=args.BLOSUM,
             only_core=args.only_core,
             muscle_path=muscle_path,
             log_file_path=log_file_path
            )


    
    shutil.make_archive(zip_file_path, 'zip', zip_file_path)
    log_message(log_file_path, f"Results saved zip file: {zip_file_path}.zip")

    document_root = "/var/www/services"
    download_path = zip_file_path.replace(document_root, "")
    print('<img src="https://raw.githubusercontent.com/morth-lab/EnZight/main/logo.svg" width="200">')
    print(f'<a href="{download_path}.zip" download>Download here</a>')


if __name__ == "__main__":
    main()
