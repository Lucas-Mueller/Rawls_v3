from diagrams import Diagram, Cluster
from diagrams.programming.language import Python
from diagrams.generic.device import Mobile
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.compute import Server
from diagrams.generic.storage import Storage

with Diagram("System Architecture", show=False, filename="documentation/system_architecture"):
    user = Mobile("User")

    with Cluster("Rawls Framework"):
        main = Python("main.py")

        with Cluster("Core Components"):
            exp_manager = Airflow("Experiment Manager")
            phase1 = Airflow("Phase 1 Manager")
            phase2 = Airflow("Phase 2 Manager")

        with Cluster("Agents"):
            participant_agent = Server("Participant Agent")
            utility_agent = Server("Utility Agent")

        with Cluster("Configuration"):
            config = Storage("Config YAML")

        main >> exp_manager
        exp_manager >> phase1
        exp_manager >> phase2
        phase1 >> participant_agent
        phase2 >> utility_agent
        main << config

    user >> main