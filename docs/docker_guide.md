# Docker for Robotics: Essentials & Troubleshooting

## The "Localhost" Trap
Inside a container, `localhost` resolves to that container itself, NOT the host machine. 
To communicate between a 3-container stack (`gazebo`, `arducopter`, `ap_gazebo`), you must use their container names as the hostname over the Docker network.

## The 3-Step Verification
If Docker breaks, run these in order to isolate the failure:
1. `docker version` (Checks if CLI can talk to the daemon. Permission issues show up here).
2. `docker info` (Checks the server state, storage, and networking).
3. `docker run hello-world` (Checks pulling, building, and executing).

## Essential Commands

* **List running containers:**
  `docker ps`
  *(Add `-a` to see stopped containers as well).*

* **List downloaded images (formatted cleanly):**
  `docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'`
  *(Shows what base environments you have downloaded onto your hard drive).*

* **Check disk usage:**
  `docker system df`
  *(Shows exactly how much space images, containers, and build caches are consuming).*

* **Clean up the system:**
  `docker system prune`
  *(WARNING: Deletes all stopped containers, unused networks, and dangling images. Excellent for freeing up hard drive space).*
