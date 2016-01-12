# Export MKS (PTC) Integrity to GIT
* This python script will export the project history from MKS (PTC) Integrity to a GIT repository
* Currently imports checkpoints and development paths only
* This does not currently support incremental imports

## HOW TO USE
1. You must have python, si (MKS/PTC command line tools), and git on the PATH variable
2. Make a folder for where you want your git repository to reside
3. Initialize the git repository by running "git init"
4. Execute the respective command for cygwin ```./mks_checkpoints_to_git.py <MKS_project_path/project.pj> | git fast-import``` or for windows ```python mks_checkpoints_to_git.py <MKS_project_path/project.pj> | git fast-import``` from within the initialized git repository (this will take awhile depending on how big your project is)
5. Once the import is complete, git will output import statistics
