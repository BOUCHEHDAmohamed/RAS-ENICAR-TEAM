import os import numpy as np import matplotlib.pyplot as plt from PIL import Image import random

DATASET_PATH = "/kaggle/input/datasets/lukpellant/droneflight-obs-avoidanceairsimrgbdepth10k-320x320/data_collected_potential_final_v58_mod25_320x320_cmds"

RGB_PATH = os.path.join(DATASET_PATH, "rgb") DEPTH_PATH = os.path.join(DATASET_PATH, "depth") CMD_PATH = os.path.join(DATASET_PATH, "commands")

print("RGB files:", len(os.listdir(RGB_PATH))) print("Depth files:", len(os.listdir(DEPTH_PATH))) print("Command files:", len(os.listdir(CMD_PATH)))

add Codeadd Markdown
files = sorted(os.listdir(RGB_PATH)) sample_file = random.choice(files)

print("Sample file:", sample_file)

add Codeadd Markdown
depth_file = sample_file.replace(".png", ".npy") depth_map = np.load(os.path.join(DEPTH_PATH, depth_file))

print("Depth shape:", depth_map.shape) print("Depth min:", depth_map.min()) print("Depth max:", depth_map.max())

add Codeadd Markdown
cmd_file = sample_file.replace(".png", ".npy") command = np.load(os.path.join(CMD_PATH, cmd_file))

print("Command vector:", command) print("Command shape:", command.shape)

add Codeadd Markdown
pip install torch torchvision timm opencv-python tqdm matplotlib

add Codeadd Markdown
import os import numpy as np import cv2 from PIL import Image from tqdm import tqdm

import torch import torch.nn as nn from torch.utils.data import Dataset, DataLoader import timm

add Codeadd Markdown
DATASET_PATH = "/kaggle/input/datasets/lukpellant/droneflight-obs-avoidanceairsimrgbdepth10k-320x320/data_collected_potential_final_v58_mod25_320x320_cmds"

RGB_PATH = os.path.join(DATASET_PATH, "rgb") DEPTH_PATH = os.path.join(DATASET_PATH, "depth") CMD_PATH = os.path.join(DATASET_PATH, "commands")

print("RGB_PATH exists:", os.path.exists(RGB_PATH)) print("DEPTH_PATH exists:", os.path.exists(DEPTH_PATH)) print("CMD_PATH exists:", os.path.exists(CMD_PATH))

class DroneDataset(Dataset): def init(self): self.files = sorted(os.listdir(RGB_PATH))

def __len__(self):
    return len(self.files)

def __getitem__(self, idx):
    file = self.files[idx]

    # --- RGB ---
    rgb = Image.open(os.path.join(RGB_PATH, file))
    rgb = np.array(rgb) / 255.0
    rgb = np.transpose(rgb, (2,0,1))  # CHW

    # --- DEPTH ---
    depth = np.load(os.path.join(DEPTH_PATH, file.replace(".png",".npy")))
    depth = depth / 125.0             # normalize 0-1
    depth = np.expand_dims(depth, 0)  # add channel

    # --- COMMAND ---
    cmd = np.load(os.path.join(CMD_PATH, file.replace(".png",".npy")))

    return (
        torch.tensor(rgb, dtype=torch.float32),
        torch.tensor(depth, dtype=torch.float32),
        torch.tensor(cmd, dtype=torch.float32)
    )
add Codeadd Markdown
class DroneDataset(Dataset): def init(self): self.files = sorted(os.listdir(RGB_PATH))

def __len__(self):
    return len(self.files)

def __getitem__(self, idx):
    file = self.files[idx]

    # ---- RGB ----
    rgb = cv2.imread(os.path.join(RGB_PATH, file))
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (320,320))
    rgb = rgb.astype(np.float32) / 255.0
    rgb = np.transpose(rgb, (2,0,1))
    

    # ---- DEPTH ----
    depth = np.load(os.path.join(DEPTH_PATH, file.replace(".png",".npy")))
    depth = depth.astype(np.float32) / 125.0
    depth = np.expand_dims(depth, 0)

    # ---- COMMAND ----
   cmd = np.load(os.path.join(CMD_PATH, file.replace(".png",".npy"))).astype(np.float32)
NORMALIZE COMMANDS (CRITICAL)
cmd[0] /= 5.0 # vx cmd[1] /= 5.0 # vy cmd[2] /= 5.0 # vz cmd[3] /= 1.0 # yaw

    return (
        torch.tensor(rgb),
        torch.tensor(depth),
        torch.tensor(cmd)
    )
add Codeadd Markdown
dataset = DroneDataset() print("Dataset size:", len(dataset))

add Codeadd Markdown
from torch.utils.data import random_split train_size = int(0.8 * len(dataset)) val_size = len(dataset) - train_size

train_ds, val_ds = random_split(dataset, [train_size, val_size])

print("Train:", len(train_ds)) print("Val:", len(val_ds))

add Codeadd Markdown
train_loader = DataLoader( train_ds, batch_size=32, shuffle=True, num_workers=4, pin_memory=True )

val_loader = DataLoader( val_ds, batch_size=32, num_workers=4, pin_memory=True )

add Codeadd Markdown
class DroneNet(nn.Module): def init(self): super().init()

    # ---------- RGB BACKBONE ----------
    self.rgb_backbone = timm.create_model(
        "efficientnet_b0",
        pretrained=True,
        num_classes=0
    )

    # 🔥 UNFREEZE EfficientNet (fine-tuning)
    for param in self.rgb_backbone.parameters():
        param.requires_grad = True

    # ---------- DEPTH BRANCH ----------
    self.depth_branch = nn.Sequential(
        nn.Conv2d(1,16,3,2,1), nn.ReLU(),
        nn.Conv2d(16,32,3,2,1), nn.ReLU(),
        nn.Conv2d(32,64,3,2,1), nn.ReLU(),
        nn.AdaptiveAvgPool2d(1)
    )

    # ---------- FUSION HEAD ----------
    self.fc = nn.Sequential(
        nn.Linear(1280+64,256), nn.ReLU(),
        nn.Linear(256,64), nn.ReLU(),
        nn.Linear(64,4)
    )

def forward(self, rgb, depth):
    rgb_feat = self.rgb_backbone(rgb)
    depth_feat = self.depth_branch(depth).view(depth.size(0), -1)
    x = torch.cat([rgb_feat, depth_feat], dim=1)
    return self.fc(x)
add Codeadd Markdown
device = "cuda" if torch.cuda.is_available() else "cpu" model = DroneNet().to(device)

criterion = nn.SmoothL1Loss() optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau( optimizer, factor=0.5, patience=2 )

add Codeadd Markdown
best_loss = 999 train_losses, val_losses = [], []

for epoch in range(40):

# TRAIN
model.train()
train_loss = 0
for rgb, depth, cmd in tqdm(train_loader):
    rgb, depth, cmd = rgb.to(device), depth.to(device), cmd.to(device)

    pred = model(rgb, depth)
    loss = criterion(pred, cmd)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    train_loss += loss.item()

train_loss /= len(train_loader)
train_losses.append(train_loss)

# VALIDATION
model.eval()
val_loss = 0
all_preds, all_targets = [], []

with torch.no_grad():
    for rgb, depth, cmd in val_loader:
        rgb, depth, cmd = rgb.to(device), depth.to(device), cmd.to(device)
        pred = model(rgb, depth)

        loss = criterion(pred, cmd)
        val_loss += loss.item()

        all_preds.append(pred.cpu().numpy())
        all_targets.append(cmd.cpu().numpy())

val_loss /= len(val_loader)
val_losses.append(val_loss)
scheduler.step(val_loss)

print(f"Epoch {epoch} | Train {train_loss:.4f} | Val {val_loss:.4f}")

if val_loss < best_loss:
    best_loss = val_loss
    torch.save(model.state_dict(), "drone_best_model.pth")
    print("🔥 BEST MODEL SAVED")
