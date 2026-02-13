# InMoov URDF Project

This repository provides a fully functional **Unified Robot Description Format (URDF)** model for the **InMoov** robot platform.

## 📌 Overview

**InMoov** is an open-source, 3D-printed, life-size humanoid robot created by **Gael Langevin**. This project aims to deliver a comprehensive and precise **URDF description** of the InMoov robot for use in **simulation** and **robotics development** environments.

The URDF file was created using **[Blender](https://www.blender.org/)** (version **4.3.2**) with the **[Phobos](https://github.com/dfki-ric/phobos)** add-on.  
Currently, the export uses **STL** files, but you can export in other formats directly from Blender using **Phobos**.

---

## 🚀 Features

✔️ **Complete URDF model** of the InMoov robot  
✔️ **Accurate joint configurations** and limits  
✔️ **ROS-compatible** (Robot Operating System)  
✔️ **Ready for simulation** in **Gazebo**, **RViz**, and other robotics environments

---

## 📖 Documentation

For more details on **creation processes**, **troubleshooting**, and other guidance, visit the **[Sentience Robotics documentation](https://docs.sentience-robotics.tech/s/master/p/urdf-NyIKx8PezV)**.

---

## 📂 Files & Folder Structure

📦 InMoov-URDF-Project<br>
├── 📄 URDF.blend # Blender file with Phobos configurations<br>
├── 📄 Stand.blend # Blender file containing a stand for the upper body<br>
├── 📂 InMoov # Folder containing the URDF export and STL meshes<br>

---

## Adapt Phobos Export to Xacro
The current URDF export is in a standard format. To adapt it for use with **Xacro** (XML Macros), you can follow these steps:
Rename inmoov/urdf/inmoov.urdf to inmoov/3dmodel/robot_description.urdf.xacro

---

## 🔍 Help Us Improve the InMoov URDF

We currently include **handsI1** and **headI1**, but we aim to integrate the latest **headI2** and **handsI2** models.

📢 **We need your help!**  
If you have access to **headI2** and **handsI2** Blender files or related resources, please contribute to this open-source effort.

Let's **enhance** the accuracy and usability of the **InMoov simulation** together! 🚀

Feel free to share any leads or files with us.

---

## 📜 Code of Conduct

We value the participation of each member of our community and are committed to ensuring that every interaction is respectful and productive. To foster a positive environment, we ask you to read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

By participating in this project, you agree to uphold this code in all your interactions, both online and offline. Let's work together to maintain a welcoming and inclusive community for everyone.

If you encounter any issues or have questions regarding the Code of Conduct, please contact us at [contact@sentience-robotics.fr](mailto:contact@sentience-robotics.fr).

Thank you for being a part of our community!

---

## 🤝 Contributing

To find out more on how you can contribute to the project, please check our [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 License and Attribution

### Project License

- **Original project code/files:** GNU GPL V3 License
- **InMoov-derived files:** CC BY-NC 4.0 (as specified below)
 
See the [LICENSE](LICENSE) file for details.

### InMoov-Derived Components

Parts of this project that are derived from InMoov files (including Blender models, CAD files, and STL files) are based on the original work by **Gael Langevin**.

**Original Work:** InMoov by Gael Langevin  
**License:** [Creative Commons Attribution-NonCommercial (CC BY-NC)](https://creativecommons.org/licenses/by-nc/4.0/)  
**Source:** http://inmoov.fr/  
**Applies to:** Blender files, CAD files, STL files, and other 3D models derived from InMoov

---

## 🙌 Acknowledgments

- 🎉 [InMoov Project](https://inmoov.fr/) – Original design by Gael Langevin<br>
- 🎉 **All contributors** to the InMoov community<br>

---

## 📬 Contact

- 📧 Email: [contact@sentience-robotics.tech](mailto:contact@sentience-robotics.tech)<br>
- 🌍 GitHub Organization: [Sentience Robotics](https://github.com/sentience-robotics)<br>---

---

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.0-4baaaa.svg)](code_of_conduct.md)
