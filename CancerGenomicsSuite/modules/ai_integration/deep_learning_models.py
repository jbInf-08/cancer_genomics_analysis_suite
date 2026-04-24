"""
Deep Learning Models for Cancer Genomics Analysis

This module implements state-of-the-art deep learning architectures specifically
designed for genomic sequence analysis, mutation prediction, drug response
prediction, and multi-omics integration.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pickle
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Deep learning frameworks
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

# Scientific computing
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

# Bioinformatics
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import molecular_weight, GC

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for deep learning models."""
    sequence_length: int = 1000
    embedding_dim: int = 128
    hidden_dim: int = 256
    num_layers: int = 3
    dropout: float = 0.3
    learning_rate: float = 0.001
    batch_size: int = 32
    num_epochs: int = 100
    device: str = "auto"


class GenomicSequenceDataset(Dataset):
    """Custom dataset for genomic sequences."""
    
    def __init__(self, sequences: List[str], labels: List[int], 
                 sequence_length: int = 1000, tokenizer=None):
        self.sequences = sequences
        self.labels = labels
        self.sequence_length = sequence_length
        self.tokenizer = tokenizer or self._default_tokenizer
        
    def _default_tokenizer(self, sequence: str) -> torch.Tensor:
        """Default nucleotide tokenizer (A=0, T=1, G=2, C=3)."""
        mapping = {'A': 0, 'T': 1, 'G': 2, 'C': 3, 'N': 4}
        tokens = [mapping.get(nuc, 4) for nuc in sequence.upper()]
        
        # Pad or truncate to sequence_length
        if len(tokens) > self.sequence_length:
            tokens = tokens[:self.sequence_length]
        else:
            tokens.extend([4] * (self.sequence_length - len(tokens)))
            
        return torch.tensor(tokens, dtype=torch.long)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = self.sequences[idx]
        label = self.labels[idx]
        
        tokens = self.tokenizer(sequence)
        return tokens, torch.tensor(label, dtype=torch.long)


class GenomicCNN(nn.Module):
    """Convolutional Neural Network for genomic sequence analysis."""
    
    def __init__(self, config: ModelConfig, num_classes: int = 2):
        super(GenomicCNN, self).__init__()
        self.config = config
        
        # Embedding layer for nucleotides
        self.embedding = nn.Embedding(5, config.embedding_dim)  # 5 for A,T,G,C,N
        
        # Convolutional layers
        self.conv_layers = nn.ModuleList([
            nn.Conv1d(config.embedding_dim, 64, kernel_size=3, padding=1),
            nn.Conv1d(64, 128, kernel_size=5, padding=2),
            nn.Conv1d(128, 256, kernel_size=7, padding=3),
        ])
        
        # Batch normalization and dropout
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(64),
            nn.BatchNorm1d(128),
            nn.BatchNorm1d(256),
        ])
        
        # Global average pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Fully connected layers
        self.fc_layers = nn.Sequential(
            nn.Linear(256, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim // 2, num_classes)
        )
        
    def forward(self, x):
        # Embedding
        x = self.embedding(x)  # (batch_size, seq_len, embedding_dim)
        x = x.transpose(1, 2)  # (batch_size, embedding_dim, seq_len)
        
        # Convolutional layers
        for conv, bn in zip(self.conv_layers, self.batch_norms):
            x = F.relu(bn(conv(x)))
            x = F.max_pool1d(x, kernel_size=2)
        
        # Global pooling
        x = self.global_pool(x)  # (batch_size, 256, 1)
        x = x.squeeze(-1)  # (batch_size, 256)
        
        # Fully connected layers
        x = self.fc_layers(x)
        return x


class GenomicLSTM(nn.Module):
    """LSTM network for genomic sequence analysis."""
    
    def __init__(self, config: ModelConfig, num_classes: int = 2):
        super(GenomicLSTM, self).__init__()
        self.config = config
        
        # Embedding layer
        self.embedding = nn.Embedding(5, config.embedding_dim)
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=config.embedding_dim,
            hidden_size=config.hidden_dim,
            num_layers=config.num_layers,
            dropout=config.dropout if config.num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=config.hidden_dim * 2,
            num_heads=8,
            dropout=config.dropout,
            batch_first=True
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(config.hidden_dim * 2, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim, num_classes)
        )
        
    def forward(self, x):
        # Embedding
        x = self.embedding(x)  # (batch_size, seq_len, embedding_dim)
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Self-attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Global average pooling
        pooled = torch.mean(attn_out, dim=1)
        
        # Classification
        output = self.classifier(pooled)
        return output


class TransformerGenomicModel(nn.Module):
    """Transformer model for genomic sequence analysis."""
    
    def __init__(self, config: ModelConfig, num_classes: int = 2):
        super(TransformerGenomicModel, self).__init__()
        self.config = config
        
        # Embedding layer
        self.embedding = nn.Embedding(5, config.embedding_dim)
        self.positional_encoding = nn.Parameter(
            torch.randn(config.sequence_length, config.embedding_dim)
        )
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.embedding_dim,
            nhead=8,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_layers
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(config.embedding_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim, num_classes)
        )
        
    def forward(self, x):
        # Embedding and positional encoding
        x = self.embedding(x) + self.positional_encoding[:x.size(1)]
        
        # Transformer
        x = self.transformer(x)
        
        # Global average pooling
        x = torch.mean(x, dim=1)
        
        # Classification
        output = self.classifier(x)
        return output


class GenomicSequenceAnalyzer:
    """Main class for genomic sequence analysis using deep learning."""
    
    def __init__(self, config: ModelConfig = None, model_type: str = "cnn"):
        self.config = config or ModelConfig()
        self.model_type = model_type
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        
        # Initialize model
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the selected model architecture."""
        if self.model_type == "cnn":
            self.model = GenomicCNN(self.config)
        elif self.model_type == "lstm":
            self.model = GenomicLSTM(self.config)
        elif self.model_type == "transformer":
            self.model = TransformerGenomicModel(self.config)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        self.model.to(self.device)
        logger.info(f"Initialized {self.model_type} model on {self.device}")
    
    def prepare_data(self, sequences: List[str], labels: List[Any]) -> Tuple[DataLoader, DataLoader]:
        """Prepare data for training."""
        # Encode labels
        encoded_labels = self.label_encoder.fit_transform(labels)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            sequences, encoded_labels, test_size=0.2, random_state=42, stratify=encoded_labels
        )
        
        # Create datasets
        train_dataset = GenomicSequenceDataset(X_train, y_train, self.config.sequence_length)
        test_dataset = GenomicSequenceDataset(X_test, y_test, self.config.sequence_length)
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=self.config.batch_size, shuffle=False)
        
        return train_loader, test_loader
    
    def train(self, sequences: List[str], labels: List[Any], 
              validation_data: Optional[Tuple[List[str], List[Any]]] = None) -> Dict[str, Any]:
        """Train the genomic sequence analyzer."""
        logger.info(f"Training {self.model_type} model on {len(sequences)} sequences")
        
        # Prepare data
        train_loader, test_loader = self.prepare_data(sequences, labels)
        
        # Initialize optimizer and loss function
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        self.model.train()
        train_losses = []
        train_accuracies = []
        
        for epoch in range(self.config.num_epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(self.device), target.to(self.device)
                
                optimizer.zero_grad()
                output = self.model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()
            
            avg_loss = epoch_loss / len(train_loader)
            accuracy = 100 * correct / total
            
            train_losses.append(avg_loss)
            train_accuracies.append(accuracy)
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Loss = {avg_loss:.4f}, Accuracy = {accuracy:.2f}%")
        
        # Evaluate on test set
        test_metrics = self.evaluate(test_loader)
        
        self.is_trained = True
        
        return {
            'train_losses': train_losses,
            'train_accuracies': train_accuracies,
            'test_metrics': test_metrics,
            'model_type': self.model_type,
            'num_epochs': self.config.num_epochs
        }
    
    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """Evaluate the model on test data."""
        self.model.eval()
        correct = 0
        total = 0
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                _, predicted = torch.max(output.data, 1)
                
                total += target.size(0)
                correct += (predicted == target).sum().item()
                
                all_predictions.extend(predicted.cpu().numpy())
                all_targets.extend(target.cpu().numpy())
        
        accuracy = 100 * correct / total
        precision = precision_score(all_targets, all_predictions, average='weighted')
        recall = recall_score(all_targets, all_predictions, average='weighted')
        f1 = f1_score(all_targets, all_predictions, average='weighted')
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }
    
    def predict(self, sequences: List[str]) -> Dict[str, Any]:
        """Predict labels for new sequences."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        self.model.eval()
        predictions = []
        probabilities = []
        
        with torch.no_grad():
            for sequence in sequences:
                # Tokenize sequence
                dataset = GenomicSequenceDataset([sequence], [0], self.config.sequence_length)
                data_loader = DataLoader(dataset, batch_size=1, shuffle=False)
                
                for data, _ in data_loader:
                    data = data.to(self.device)
                    output = self.model(data)
                    prob = F.softmax(output, dim=1)
                    _, predicted = torch.max(output, 1)
                    
                    predictions.append(predicted.cpu().item())
                    probabilities.append(prob.cpu().numpy()[0])
        
        # Decode predictions
        decoded_predictions = self.label_encoder.inverse_transform(predictions)
        
        return {
            'predictions': decoded_predictions.tolist(),
            'probabilities': probabilities,
            'confidence': [max(prob) for prob in probabilities]
        }
    
    def save_model(self, filepath: str):
        """Save the trained model."""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_data = {
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'model_type': self.model_type,
            'label_encoder': self.label_encoder,
            'is_trained': self.is_trained
        }
        
        torch.save(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model."""
        model_data = torch.load(filepath, map_location=self.device)
        
        self.config = model_data['config']
        self.model_type = model_data['model_type']
        self.label_encoder = model_data['label_encoder']
        self.is_trained = model_data['is_trained']
        
        # Reinitialize model
        self._initialize_model()
        self.model.load_state_dict(model_data['model_state_dict'])
        
        logger.info(f"Model loaded from {filepath}")


class MutationEffectPredictor:
    """Deep learning model for predicting mutation effects."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        
    def _create_mutation_features(self, mutation_data: Dict[str, Any]) -> torch.Tensor:
        """Create feature vector for mutation prediction."""
        features = []
        
        # Sequence features
        if 'sequence' in mutation_data:
            seq = mutation_data['sequence']
            features.extend([
                len(seq),
                seq.count('A') / len(seq),
                seq.count('T') / len(seq),
                seq.count('G') / len(seq),
                seq.count('C') / len(seq),
                GC(seq) / 100
            ])
        
        # Mutation type features
        mutation_type = mutation_data.get('type', 'SNP')
        type_features = [0] * 5  # SNP, insertion, deletion, indel, complex
        if mutation_type == 'SNP':
            type_features[0] = 1
        elif mutation_type == 'insertion':
            type_features[1] = 1
        elif mutation_type == 'deletion':
            type_features[2] = 1
        elif mutation_type == 'indel':
            type_features[3] = 1
        else:
            type_features[4] = 1
        features.extend(type_features)
        
        # Conservation scores
        features.extend([
            mutation_data.get('conservation_score', 0.5),
            mutation_data.get('phylop_score', 0.0),
            mutation_data.get('gerp_score', 0.0)
        ])
        
        # Functional annotations
        features.extend([
            1 if mutation_data.get('in_coding_region', False) else 0,
            1 if mutation_data.get('in_conserved_domain', False) else 0,
            1 if mutation_data.get('affects_splicing', False) else 0
        ])
        
        return torch.tensor(features, dtype=torch.float32)
    
    def train(self, mutation_data: List[Dict[str, Any]], 
              effects: List[str]) -> Dict[str, Any]:
        """Train the mutation effect predictor."""
        logger.info(f"Training mutation effect predictor on {len(mutation_data)} mutations")
        
        # Create features
        X = torch.stack([self._create_mutation_features(mut) for mut in mutation_data])
        
        # Encode effects
        effect_encoder = LabelEncoder()
        y = effect_encoder.fit_transform(effects)
        y = torch.tensor(y, dtype=torch.long)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Create model
        self.model = nn.Sequential(
            nn.Linear(X.shape[1], 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, len(effect_encoder.classes_))
        ).to(self.device)
        
        # Training
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        train_losses = []
        for epoch in range(100):
            optimizer.zero_grad()
            output = self.model(X_train.to(self.device))
            loss = criterion(output, y_train.to(self.device))
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: Loss = {loss.item():.4f}")
        
        # Evaluate
        self.model.eval()
        with torch.no_grad():
            test_output = self.model(X_test.to(self.device))
            _, predicted = torch.max(test_output, 1)
            accuracy = (predicted == y_test.to(self.device)).float().mean().item()
        
        self.is_trained = True
        self.effect_encoder = effect_encoder
        
        return {
            'train_losses': train_losses,
            'test_accuracy': accuracy,
            'num_classes': len(effect_encoder.classes_)
        }
    
    def predict_effect(self, mutation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict the effect of a mutation."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        features = self._create_mutation_features(mutation_data).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(features)
            probabilities = F.softmax(output, dim=1)
            _, predicted = torch.max(output, 1)
        
        predicted_effect = self.effect_encoder.inverse_transform([predicted.item()])[0]
        confidence = probabilities[0][predicted.item()].item()
        
        return {
            'predicted_effect': predicted_effect,
            'confidence': confidence,
            'all_probabilities': {
                effect: prob.item() 
                for effect, prob in zip(self.effect_encoder.classes_, probabilities[0])
            }
        }


class DrugResponsePredictor:
    """Deep learning model for predicting drug response."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        
    def _create_drug_features(self, genomic_data: Dict[str, Any], 
                            drug_data: Dict[str, Any]) -> torch.Tensor:
        """Create feature vector for drug response prediction."""
        features = []
        
        # Genomic features
        features.extend([
            genomic_data.get('mutation_count', 0),
            genomic_data.get('cnv_count', 0),
            genomic_data.get('expression_level', 0.0),
            genomic_data.get('methylation_level', 0.5)
        ])
        
        # Drug features
        features.extend([
            drug_data.get('molecular_weight', 0.0),
            drug_data.get('logp', 0.0),
            drug_data.get('hbd_count', 0),
            drug_data.get('hba_count', 0)
        ])
        
        # Interaction features
        features.extend([
            genomic_data.get('target_gene_expression', 0.0),
            genomic_data.get('pathway_activity', 0.0),
            genomic_data.get('immune_score', 0.0)
        ])
        
        return torch.tensor(features, dtype=torch.float32)
    
    def train(self, genomic_data: List[Dict[str, Any]], 
              drug_data: List[Dict[str, Any]], 
              responses: List[float]) -> Dict[str, Any]:
        """Train the drug response predictor."""
        logger.info(f"Training drug response predictor on {len(genomic_data)} samples")
        
        # Create features
        X = torch.stack([
            self._create_drug_features(gen, drug) 
            for gen, drug in zip(genomic_data, drug_data)
        ])
        
        y = torch.tensor(responses, dtype=torch.float32)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create model
        self.model = nn.Sequential(
            nn.Linear(X.shape[1], 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        ).to(self.device)
        
        # Training
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        train_losses = []
        for epoch in range(100):
            optimizer.zero_grad()
            output = self.model(X_train.to(self.device)).squeeze()
            loss = criterion(output, y_train.to(self.device))
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: Loss = {loss.item():.4f}")
        
        # Evaluate
        self.model.eval()
        with torch.no_grad():
            test_output = self.model(X_test.to(self.device)).squeeze()
            mse = F.mse_loss(test_output, y_test.to(self.device)).item()
            mae = F.l1_loss(test_output, y_test.to(self.device)).item()
        
        self.is_trained = True
        
        return {
            'train_losses': train_losses,
            'test_mse': mse,
            'test_mae': mae
        }
    
    def predict_response(self, genomic_data: Dict[str, Any], 
                        drug_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict drug response."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        features = self._create_drug_features(genomic_data, drug_data).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            response = self.model(features).item()
        
        return {
            'predicted_response': response,
            'response_category': self._categorize_response(response)
        }
    
    def _categorize_response(self, response: float) -> str:
        """Categorize response value."""
        if response < 0.3:
            return "Resistant"
        elif response < 0.7:
            return "Moderate"
        else:
            return "Sensitive"


class SurvivalAnalysisModel:
    """Deep learning model for survival analysis."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        
    def _create_survival_features(self, clinical_data: Dict[str, Any], 
                                genomic_data: Dict[str, Any]) -> torch.Tensor:
        """Create feature vector for survival prediction."""
        features = []
        
        # Clinical features
        features.extend([
            clinical_data.get('age', 65.0),
            clinical_data.get('stage', 2.0),
            clinical_data.get('grade', 2.0),
            1 if clinical_data.get('smoking_history', False) else 0,
            1 if clinical_data.get('family_history', False) else 0
        ])
        
        # Genomic features
        features.extend([
            genomic_data.get('mutation_burden', 0.0),
            genomic_data.get('tmb_score', 0.0),
            genomic_data.get('msi_status', 0.0),
            genomic_data.get('pdl1_expression', 0.0)
        ])
        
        return torch.tensor(features, dtype=torch.float32)
    
    def train(self, clinical_data: List[Dict[str, Any]], 
              genomic_data: List[Dict[str, Any]], 
              survival_times: List[float], 
              events: List[bool]) -> Dict[str, Any]:
        """Train the survival analysis model."""
        logger.info(f"Training survival model on {len(clinical_data)} patients")
        
        # Create features
        X = torch.stack([
            self._create_survival_features(clin, gen) 
            for clin, gen in zip(clinical_data, genomic_data)
        ])
        
        y_time = torch.tensor(survival_times, dtype=torch.float32)
        y_event = torch.tensor(events, dtype=torch.float32)
        
        # Split data
        X_train, X_test, y_time_train, y_time_test, y_event_train, y_event_test = train_test_split(
            X, y_time, y_event, test_size=0.2, random_state=42
        )
        
        # Create model
        self.model = nn.Sequential(
            nn.Linear(X.shape[1], 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1)
        ).to(self.device)
        
        # Training
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        train_losses = []
        for epoch in range(100):
            optimizer.zero_grad()
            output = self.model(X_train.to(self.device)).squeeze()
            loss = criterion(output, y_time_train.to(self.device))
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: Loss = {loss.item():.4f}")
        
        # Evaluate
        self.model.eval()
        with torch.no_grad():
            test_output = self.model(X_test.to(self.device)).squeeze()
            mse = F.mse_loss(test_output, y_time_test.to(self.device)).item()
        
        self.is_trained = True
        
        return {
            'train_losses': train_losses,
            'test_mse': mse
        }
    
    def predict_survival(self, clinical_data: Dict[str, Any], 
                        genomic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict survival time."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        features = self._create_survival_features(clinical_data, genomic_data).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            survival_time = self.model(features).item()
        
        return {
            'predicted_survival_time': survival_time,
            'risk_category': self._categorize_risk(survival_time)
        }
    
    def _categorize_risk(self, survival_time: float) -> str:
        """Categorize risk based on survival time."""
        if survival_time < 12:
            return "High Risk"
        elif survival_time < 36:
            return "Medium Risk"
        else:
            return "Low Risk"


class MultiOmicsIntegrator:
    """Deep learning model for multi-omics data integration."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.models = {}
        self.integrator = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        
    def _create_omics_encoders(self, omics_data: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        """Create encodings for different omics data types."""
        encodings = {}
        
        # Genomics encoding
        if 'genomics' in omics_data:
            genomics = omics_data['genomics']
            encodings['genomics'] = torch.tensor([
                genomics.get('mutation_count', 0),
                genomics.get('cnv_count', 0),
                genomics.get('sv_count', 0)
            ], dtype=torch.float32)
        
        # Transcriptomics encoding
        if 'transcriptomics' in omics_data:
            transcriptomics = omics_data['transcriptomics']
            encodings['transcriptomics'] = torch.tensor([
                transcriptomics.get('expression_mean', 0.0),
                transcriptomics.get('expression_std', 0.0),
                transcriptomics.get('differential_genes', 0)
            ], dtype=torch.float32)
        
        # Proteomics encoding
        if 'proteomics' in omics_data:
            proteomics = omics_data['proteomics']
            encodings['proteomics'] = torch.tensor([
                proteomics.get('protein_abundance', 0.0),
                proteomics.get('phosphorylation', 0.0),
                proteomics.get('ubiquitination', 0.0)
            ], dtype=torch.float32)
        
        return encodings
    
    def train(self, omics_data: List[Dict[str, Any]], 
              labels: List[Any]) -> Dict[str, Any]:
        """Train the multi-omics integrator."""
        logger.info(f"Training multi-omics integrator on {len(omics_data)} samples")
        
        # Create encodings for each omics type
        omics_encodings = {}
        for omics_type in ['genomics', 'transcriptomics', 'proteomics']:
            encodings = []
            for data in omics_data:
                if omics_type in data:
                    encoding = self._create_omics_encoders(data)[omics_type]
                    encodings.append(encoding)
                else:
                    # Zero encoding for missing data
                    encodings.append(torch.zeros(3))
            
            if encodings:
                omics_encodings[omics_type] = torch.stack(encodings)
        
        # Create individual encoders for each omics type
        for omics_type, encodings in omics_encodings.items():
            self.models[omics_type] = nn.Sequential(
                nn.Linear(encodings.shape[1], 64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, 32)
            ).to(self.device)
        
        # Create integrator
        total_features = len(omics_encodings) * 32
        self.integrator = nn.Sequential(
            nn.Linear(total_features, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, len(set(labels)))
        ).to(self.device)
        
        # Encode labels
        label_encoder = LabelEncoder()
        encoded_labels = label_encoder.fit_transform(labels)
        y = torch.tensor(encoded_labels, dtype=torch.long)
        
        # Training
        all_params = list(self.integrator.parameters())
        for model in self.models.values():
            all_params.extend(list(model.parameters()))
        
        optimizer = optim.Adam(all_params, lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        train_losses = []
        for epoch in range(100):
            optimizer.zero_grad()
            
            # Forward pass through individual encoders
            encoded_features = []
            for omics_type, encodings in omics_encodings.items():
                encoded = self.models[omics_type](encodings.to(self.device))
                encoded_features.append(encoded)
            
            # Concatenate and pass through integrator
            combined = torch.cat(encoded_features, dim=1)
            output = self.integrator(combined)
            
            loss = criterion(output, y.to(self.device))
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: Loss = {loss.item():.4f}")
        
        self.is_trained = True
        self.label_encoder = label_encoder
        
        return {
            'train_losses': train_losses,
            'num_omics_types': len(omics_encodings),
            'num_classes': len(label_encoder.classes_)
        }
    
    def predict(self, omics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict using multi-omics data."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Create encodings
        encodings = self._create_omics_encoders(omics_data)
        
        # Forward pass
        encoded_features = []
        for omics_type, encoding in encodings.items():
            if omics_type in self.models:
                encoded = self.models[omics_type](encoding.unsqueeze(0).to(self.device))
                encoded_features.append(encoded)
        
        if not encoded_features:
            raise ValueError("No valid omics data found")
        
        # Integrate and predict
        combined = torch.cat(encoded_features, dim=1)
        output = self.integrator(combined)
        probabilities = F.softmax(output, dim=1)
        _, predicted = torch.max(output, 1)
        
        predicted_label = self.label_encoder.inverse_transform([predicted.item()])[0]
        confidence = probabilities[0][predicted.item()].item()
        
        return {
            'predicted_label': predicted_label,
            'confidence': confidence,
            'all_probabilities': {
                label: prob.item() 
                for label, prob in zip(self.label_encoder.classes_, probabilities[0])
            }
        }
