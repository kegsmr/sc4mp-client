# Contributing

Thank you for your interest in contributing to the **SimCity 4 Multiplayer Project**! We welcome contributions to both the client and server repositories, as well any other associated repositories. This document outlines the guidelines for contributions.

---

## Table of Contents

1. [How to Contribute](#how-to-contribute)  
2. [Development Guidelines](#development-guidelines)  
3. [Pull Request Process](#pull-request-process)  

---

## How to Contribute

Contributions can be made by forking the appropriate repository and submitting a pull request with your changes:  

- **SC4MP Client**: [https://github.com/kegsmr/sc4mp-client](https://github.com/kegsmr/sc4mp-client)  
- **SC4MP Server**: [https://github.com/kegsmr/sc4mp-server](https://github.com/kegsmr/sc4mp-server)  
- **SC4MP API**: [https://github.com/kegsmr/sc4mp-api](https://github.com/kegsmr/sc4mp-api)
- **SC4MP Invites**: [https://github.com/kegsmr/sc4mp-invite](https://github.com/kegsmr/sc4mp-invite)

*This repository list may be incomplete and may require future updates.*

Your pull request should aim to fix one of the posted issues, as this ensures that the contribution aligns with the project's current needs.

---

## Development Guidelines

To maintain consistency and compatibility across the project, please adhere to the following guidelines:

### 1. Python Version  
Use **Python 3.8** for all development work. This version is the latest release of Python that is compatible with Windows Vista, 7, and 8. Using a newer version would break this compatibility and could prevent the project from running on these operating systems. You can download **Python 3.8** here:  
[https://www.python.org/downloads/release/python-3810/](https://www.python.org/downloads/release/python-3810/)

### 2. External Modules  
External modules **may only be used** if they are:  
- **Already included in the project**; or  
- **Explicitly approved by the maintainers** prior to use.  

The use of external modules is discouraged for core functionalities essential to the project. If you choose to use external modules, ensure that the program remains functional even if the module is not installed.

**Example:** The module `PIL` is used in the client for rendering the server loading backgrounds (a non-essential functionality). If `PIL` is not available, server loading backgrounds are simply not rendered. Here's what this looks like in practice:

```python
try:
	from PIL import Image, ImageTk, UnidentifiedImageError
	sc4mp_has_pil = True
except ImportError:
	sc4mp_has_pil = False
```

The `LoadingBackgroundUI` then checks if the module is available and handles its absence gracefully.

### 3. Code Style  
Follow standard Python conventions as defined in [PEP 8](https://peps.python.org/pep-0008/). Make sure your code is clean, readable, and well-commented where necessary.

### 4. Testing  
Ensure your changes are tested thoroughly before submitting a pull request. This helps maintain the stability and reliability of the project.

---

## Pull Request Process

1. **Fork the Repository**  
   - Fork the relevant repository (client or server) to your own GitHub account.

2. **Clone Your Fork**  
   - Clone your fork to your local machine and create a new branch for your changes:  
     ```bash
     git clone <your-fork-url>
     cd <repository-name>
     git checkout -b <your-branch-name>
     ```

3. **Make Your Changes**  
   - Edit the code as necessary, adhering to the [Development Guidelines](#development-guidelines).  
   - Commit your changes with a clear and descriptive commit message.

4. **Submit a Pull Request**  
   - Push your branch to your forked repository:  
     ```bash
     git push origin <your-branch-name>
     ```  
   - Open a pull request on the original repository. Provide a detailed description of the changes you’ve made, referencing any related issue if applicable.

5. **Review Process**  
   - Your pull request will be reviewed by the maintainers. Note that **not all pull requests are guaranteed to be accepted**, but those that best address existing issues will be prioritized.

---

Thank you for contributing to the SimCity 4 Multiplayer Project! Your efforts help improve the experience for everyone in the community.
