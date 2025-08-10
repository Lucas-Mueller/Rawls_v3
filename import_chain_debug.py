#!/usr/bin/env python3
"""
Script to analyze the import chain and identify circular dependencies.
"""

def analyze_import_chain():
    """Analyze the import chain causing the circular dependency."""
    
    print("CIRCULAR IMPORT ANALYSIS")
    print("=" * 60)
    
    print("\nImport Chain Analysis:")
    print("1. main.py imports:")
    print("   -> core.experiment_manager.FrohlichExperimentManager")
    
    print("\n2. core/__init__.py imports:")
    print("   -> .distribution_generator.DistributionGenerator")
    print("   -> .phase1_manager.Phase1Manager")
    print("   -> .phase2_manager.Phase2Manager") 
    print("   -> .experiment_manager.FrohlichExperimentManager")
    
    print("\n3. core/distribution_generator.py imports:")
    print("   -> utils.language_manager.get_language_manager")
    
    print("\n4. utils/__init__.py imports:")
    print("   -> .experiment_runner (functions)")
    
    print("\n5. utils/experiment_runner.py imports:")
    print("   -> core.experiment_manager.FrohlichExperimentManager")
    
    print("\n6. core/experiment_manager.py imports:")
    print("   -> core.Phase1Manager, Phase2Manager (from core)")
    
    print("\nCIRCULAR DEPENDENCY IDENTIFIED:")
    print("core/__init__.py -> distribution_generator -> utils.language_manager")
    print("-> utils/__init__.py -> experiment_runner -> core.experiment_manager")
    print("-> core (Phase1Manager, Phase2Manager)")
    print("\nThis creates a circular import loop!")

if __name__ == "__main__":
    analyze_import_chain()