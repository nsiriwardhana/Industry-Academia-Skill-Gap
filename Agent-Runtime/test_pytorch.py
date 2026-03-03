"""
Quick test to verify PyTorch installation and DLL loading
"""
try:
    import torch
    print("✅ PyTorch imported successfully!")
    print(f"Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU")
    
    # Test basic tensor operation
    x = torch.tensor([1, 2, 3])
    print(f"Test tensor: {x}")
    print("✅ PyTorch is working correctly!")
    
except Exception as e:
    print(f"❌ PyTorch error: {e}")
    print("\nThis typically means:")
    print("1. Visual C++ Redistributable is not installed")
    print("2. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    print("3. Install and restart your computer")
