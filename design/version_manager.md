# Version Manager

The Version Manager is a server that provides version routing for the various available versions of the system. It exposes a `/versions` endpoint (which returns the output depending on the status of the remote repo) and forwards queries of the type `/agent/{version}/...` to the corresponding port. It might make sense to have a way for each version to "register" an internal port in which it can be run.

Note: there is no "top" version because it's an evolving tree.