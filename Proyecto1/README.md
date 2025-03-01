# Descargar el repositorio #
para descargar el repositorio puedes hacer uso del siguiente comando
```bash
git clone https://github.com/bricj/MLOPS_PUJ_Workspace.git 
```

Luego, debes ubicarte en la carpeta del repositorio y navegar hacia la carpeta **Proyecto1**.
Una vez en la carpeta vas a crear la imagen Docker y su contenedor asociado  escribiendo en la terminal
```bash
docker-compose  up --build
```
.

una vez que se ha creado adecuadamente la imagen Docker y el contenedor ya se encuentre en funcionamiento, tendrás disponible en la terminal 
un enlace muy similar a este: ```http://127.0.0.1:8888/lab?token=access-token```. Copialo y pégalo en tu navegador para acceder al entorno de jupyter lab.

# visualización y ejecución del Notebook #