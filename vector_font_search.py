# vector_font_search.py
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import os
import shutil
import pickle
from datetime import datetime


class VectorFontSearch:

    def __init__(self,
                 model_name: str = 'all-MiniLM-L6-v2',
                 images_dir: Optional[str] = None):
        """Initialize the vector-based font search system."""
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.images_dir = Path(images_dir) if images_dir else None

        # Initialize storage
        self.documents = []
        self.index = faiss.IndexFlatIP(self.dimension)

        # Metadata
        self.metadata = {
            "model_name": model_name,
            "dimension": self.dimension,
            "created_at": datetime.now().isoformat(),
            "num_documents": 0,
            "last_updated": None
        }

    def save(self, save_dir: str) -> None:
        """
        Save the complete search state including index, documents, and metadata.
        
        Args:
            save_dir: Directory to save the search state
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Update metadata
            self.metadata.update({
                "num_documents": len(self.documents),
                "last_updated": datetime.now().isoformat()
            })

            # Save FAISS index
            index_path = save_dir / "font_index.faiss"
            faiss.write_index(self.index, str(index_path))

            # Save documents
            docs_path = save_dir / "documents.json"
            with open(docs_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)

            # Save metadata
            meta_path = save_dir / "metadata.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

            print(f"Successfully saved search state to {save_dir}")
            print(f"- Documents: {len(self.documents)}")
            print(
                f"- Index size: {os.path.getsize(index_path) / 1024 / 1024:.2f} MB"
            )

        except Exception as e:
            print(f"Error saving search state: {str(e)}")
            raise

    @classmethod
    def load(cls,
             save_dir: str,
             images_dir: Optional[str] = None) -> 'VectorFontSearch':
        """
        Load a complete search state from disk.
        
        Args:
            save_dir: Directory containing the saved search state
            images_dir: Optional new images directory
        
        Returns:
            VectorFontSearch: Loaded search instance
        """
        save_dir = Path(save_dir)

        try:
            # Load metadata first to get model name
            meta_path = save_dir / "metadata.json"
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Create instance with same model
            instance = cls(model_name=metadata["model_name"],
                           images_dir=images_dir)
            instance.metadata = metadata

            # Load FAISS index
            index_path = save_dir / "font_index.faiss"
            instance.index = faiss.read_index(str(index_path))

            # Load documents
            docs_path = save_dir / "documents.json"
            with open(docs_path, 'r', encoding='utf-8') as f:
                instance.documents = json.load(f)

            print(f"Successfully loaded search state from {save_dir}")
            print(f"- Model: {instance.model_name}")
            print(f"- Documents: {len(instance.documents)}")
            print(f"- Last updated: {metadata.get('last_updated', 'unknown')}")

            return instance

        except Exception as e:
            print(f"Error loading search state: {str(e)}")
            raise

    def add_fonts(self, font_data_list: List[Dict]) -> None:
        """Add fonts to the search index."""
        if not font_data_list:
            return

        try:
            # Prepare batch of texts
            texts = [
                self._create_searchable_text(font) for font in font_data_list
            ]

            # Compute embeddings
            embeddings = self.model.encode(texts,
                                           show_progress_bar=False,
                                           normalize_embeddings=True)

            # Add to index
            self.index.add(embeddings)

            # Store documents
            self.documents.extend(font_data_list)

            # print(f"Added {len(font_data_list)} fonts. Total: {len(self.documents)}")

        except Exception as e:
            print(f"Error adding fonts: {str(e)}")

    def search(self, query: str, k: int = 10) -> List[Dict]:
        """Search for similar fonts."""
        if not self.documents:
            print("Warning: No documents in index")
            return []

        try:
            # Encode query
            query_vector = self.model.encode([query],
                                             show_progress_bar=False,
                                             normalize_embeddings=True)

            # Search
            scores, indices = self.index.search(query_vector,
                                                min(k, len(self.documents)))

            # Prepare results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx < len(self.documents):
                    font = self.documents[idx]

                    result = {
                        'filename':
                        font['filename'],
                        'description':
                        font['description']['detailed_description'],
                        'technical_characteristics':
                        font['description']['technical_characteristics'],
                        'personality_traits':
                        font['description']['personality_traits'],
                        'practical_contexts':
                        font['description']['practical_contexts'],
                        'search_keywords':
                        font['description']['search_keywords'],
                        'score':
                        float(score)
                    }

                    if self.images_dir:
                        image_path = self.images_dir / font['filename']
                        if image_path.exists():
                            result['image'] = str(image_path)

                    results.append(result)

            return results

        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def _create_searchable_text(self, font_data: Dict) -> str:
        """Create weighted searchable text from font document."""
        desc = font_data['description']

        components = [
            desc['detailed_description'] * 2,
            ' '.join(desc['technical_characteristics']) * 2,
            ' '.join(desc['personality_traits']) * 3,
            ' '.join(desc['practical_contexts']) * 2,
            ' '.join(desc['cultural_intuition']) * 2,
            ' '.join(desc['search_keywords']) * 3
        ]

        return ' '.join(components)
