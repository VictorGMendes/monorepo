# BSC RPA Outlook Adapter

Package that includes classes to interact with outlook. Currently includes:

- `Win32Outlook`, that interacts with outlook via the pywin32 package (i.e., calling VBA functions)

## Win32Outlook

This class will work as long as the you have permission to create and interact with Windows COM objects. As far as we've experimented:

- This is the case for users running a script manually.
- This doesn't work for scripts schedulled to run via the Windows Task Scheduller on Citrix NPM VDIs.
- Lacking experimentation on RDP virtual machines
