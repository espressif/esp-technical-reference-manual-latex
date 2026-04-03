import os

# Define default module and chip labels as global variables
# Update the list in the repository settings when a new chip is introduced
DEFAULT_CHIP_LABELS = os.environ.get("CHIP_LIST")

# Get the value of CI_MERGE_REQUEST_LABELS from the environment
CI_MERGE_REQUEST_LABELS = os.environ.get("CI_MERGE_REQUEST_LABELS")

# Initialize a flag for the Release label
RELEASE_LABEL = False

# Labels to ignore in build logic besides Release
IGNORED_BUILD_LABELS = [
    "needs backport",
    "backport created",
]

if CI_MERGE_REQUEST_LABELS:
    LABELS_LIST = CI_MERGE_REQUEST_LABELS.split(",")
    # Check for the Release label
    if "Release" in LABELS_LIST:
        RELEASE_LABEL = True
        # Remove the Release label from further processing
        LABELS_LIST.remove("Release")

    # Remove ignored labels
    for ignored in IGNORED_BUILD_LABELS:
        if ignored in LABELS_LIST:
            LABELS_LIST.remove(ignored)

    CI_MERGE_REQUEST_LABELS = ",".join(LABELS_LIST)

def extract_labels():
    if not CI_MERGE_REQUEST_LABELS:
        # Scenario 1: If no module or chip label is selected,
        # build main__LANGUAGE.tex files in all CHIP_SERIES folders
        MODULE_LABELS = 'main'
        CHIP_LABELS = DEFAULT_CHIP_LABELS
        print(f"No MR labels provided. Use default module labels={MODULE_LABELS} and chip labels={CHIP_LABELS}")
    else:
        LABELS = CI_MERGE_REQUEST_LABELS.split(",")
        MODULE_LABELS = ''
        CHIP_LABELS = ''
        # Scenario 2: If both module and chip labels are selected,
        # build the specific MODULE_NAME__LANGUAGE.tex files
        # in the specific CHIP_SERIES folders
        for LABEL in LABELS:
            # Check if label is not in chip labels,
            # or not partially matches chip labels
            if LABEL not in DEFAULT_CHIP_LABELS.split(","):
                MODULE_LABELS += f",{LABEL}"
            else:
                CHIP_LABELS += f",{LABEL}"

        # Remove leading commas if they exist
        MODULE_LABELS = MODULE_LABELS.lstrip(',')
        CHIP_LABELS = CHIP_LABELS.lstrip(',')

        # Scenario 3: If no module label is selected
        # but a chip label is selected,
        # build main__LANGUAGE.tex files in the specific CHIP_SERIES folder
        if not MODULE_LABELS:
            MODULE_LABELS = 'main'

        if not CHIP_LABELS:
            print("Please provide a chip label.")

        print(f"Extract module labels={MODULE_LABELS} and chip labels={CHIP_LABELS}")

    # Export MODULE_LABELS, CHIP_LABELS, and RELEASE_LABEL as environment variables
    with open("labels.env", "w") as env_file:
        env_file.write(f"MODULE_LABELS={MODULE_LABELS}\n")
        env_file.write(f"CHIP_LABELS={CHIP_LABELS}\n")
        env_file.write(f"RELEASE_LABEL={RELEASE_LABEL}\n")

if __name__ == "__main__":
    extract_labels()
