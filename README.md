# git-configspec

This tool is used to define a set of rules on which parts of what files that
are to be checked out from a single or a group of repositories. It resembles the
config spec found in the ClearCase versioning system, and aims to enable
somewhat the same functionality in regards to select versions on file basis (as
opposed to git on a *set of files* concept).

This scripts mimics the functionality by transforming the contents of the 
(`CONFIG_SPEC`) into `git` commands. 
