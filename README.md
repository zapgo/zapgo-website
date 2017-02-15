ZapGo Website
=============
Automated Deployment:
-----------------
Tag commit with version number. E.g.  
`git tag v0.1 -m 'Version 0.1'`
	
Manual Deployment:
------------------
### Push to container registry:
1. Build the static webserver:  
   `docker build -f server/Dockerfile -t zapgo-website .`  
2. Push to Container Registry:  
   `docker tag docs-server gcr.io/zapgo-1273/zapgo-website:latest`  
   `gcloud docker -- push gcr.io/zapgo-1273/zapgo-website:latest`  
   
### Once-off setup:
1. Create a Kubernetes Cluster
2. Athenticate gcloud:  
	`gcloud auth login`  
	`gcloud config set project zapgo-1273`  
3. Connect to kubernetes cluster:  
	`gcloud container clusters get-credentials hosting-cluster --zone us-west1-a --project zapgo-1273`  
4. Letsencrypt SSL setup:  
	- Namespace:  
	  `kubectl apply -f /lego/00-namespace.yaml` 
	- ConfigMap:  
	  `kubectl apply -f /lego/configmap.yaml` 
	- LEGO Pod:  
	  `kubectl apply -f /lego/deployment.yaml`  
5. Webserver setup:  
   - `kubectl apply -f 00-namespace.yaml`  
   - `kubectl apply -f service.yaml`  
   - `kubectl apply -f deployment.yaml`  
   - `kubectl apply -f ingress-tls.yaml`  
6. Check the external IP address and setup DNS:  
   - `kubectl get ingress --namespace zapgo-website zapgo-website`  
