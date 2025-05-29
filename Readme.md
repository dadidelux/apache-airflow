![ETL Pipeline](images/pipeline_design.png)

# reference end to end 

# yt channel https://www.youtube.com/watch?v=3xyoM28B40Y&t=10s

# documentation https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html -- (Follow this if your are using Linux or Mac)

# in windows 

# powershell installation for apache airflow

# code
Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/2.9.1/docker-compose.yaml" -OutFile "docker-compose.yaml"

# power code 
New-Item -ItemType Directory -Force -Path ".\dags", ".\logs", ".\plugins", ".\config"
"AIRFLOW_UID=50000" | Out-File -Encoding ASCII -FilePath .env

# code
docker compose up airflow-init
docker compose up -d


# To run airflow

docker compose up -d

# check logs 

docker compose logs -f

# to shutdown

docker compose down