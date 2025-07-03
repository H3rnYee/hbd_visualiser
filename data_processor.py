"""
FIXED HDB Data Processor v2
- Added missing _save_cache method
- Enhanced sample data
- Improved error handling
"""

import pandas as pd
import requests
import os
import time
from datetime import datetime
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('HDBDataProcessor')

class HDBDataProcessor:
    def __init__(self, use_api=True, cache_file='hdb_data.parquet'):
        self.cache_file = cache_file
        self.df = None
        
        try:
            if use_api:
                logger.info("Attempting API data load")
                self._load_from_api()
                self._clean_data()
                self._save_cache()  # NOW DEFINED
            else:
                logger.info("Loading from cache")
                self._load_from_cache()
                
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            logger.warning("Attempting fallback methods")
            self._fallback_procedure()

    def _load_from_api(self):
        """Fetch data from API with error handling"""
        url = "https://data.gov.sg/api/action/datastore_search"
        params = {
            "resource_id": "f1765b54-a209-4718-8d38-a39237f502b3",
            "limit": 10000
        }
        
        all_records = []
        offset = 0
        total_records = None
        
        while True:
            try:
                params["offset"] = offset
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Validate API response structure
                if 'result' not in data or 'records' not in data['result']:
                    raise ValueError("Invalid API response structure")
                
                if total_records is None:
                    total_records = data["result"]["total"]
                    logger.info(f"Total records: {total_records}")
                
                records = data["result"]["records"]
                all_records.extend(records)
                offset += len(records)
                
                logger.info(f"Retrieved {offset}/{total_records} records")
                if offset >= total_records:
                    break
                    
                time.sleep(0.3)
                
            except (requests.RequestException, ValueError) as e:
                logger.error(f"API error: {e}")
                if offset > 0:  # Partial success
                    logger.warning(f"Returning partial data ({len(all_records)} records)")
                    break
                else:
                    raise
                    
        self.df = pd.DataFrame(all_records)
        logger.info(f"API data loaded with {len(self.df)} records")

    def _load_from_cache(self):
        """Load data from local cache file"""
        try:
            if os.path.exists(self.cache_file):
                logger.info(f"Loading data from cache: {self.cache_file}")
                
                # Handle different file formats
                if self.cache_file.endswith('.parquet'):
                    self.df = pd.read_parquet(self.cache_file)
                elif self.cache_file.endswith('.csv'):
                    self.df = pd.read_csv(self.cache_file)
                else:
                    raise ValueError("Unsupported cache file format")
                    
                logger.info(f"Cache loaded: {len(self.df)} records")
            else:
                logger.warning("No cache file found")
        except Exception as e:
            logger.error(f"Cache load failed: {e}")

    def _save_cache(self):  # ADDED METHOD
        """Save processed data to cache file"""
        if self.df is None or self.df.empty:
            return
            
        try:
            logger.info(f"Saving cache to {self.cache_file}")
            
            # Save in efficient format
            if self.cache_file.endswith('.parquet'):
                self.df.to_parquet(self.cache_file)
            else:
                self.df.to_csv(self.cache_file, index=False)
                
        except Exception as e:
            logger.error(f"Cache save failed: {e}")

    def _clean_data(self):
        """Robust data cleaning with type conversion"""
        if self.df is None or self.df.empty:
            logger.warning("No data to clean")
            return
            
        logger.info("Starting data cleaning")
        
        # Convert columns to proper types
        self.df['month'] = pd.to_datetime(self.df['month'], errors='coerce')
        
        # SAFE NUMERIC CONVERSION
        for col in ['resale_price', 'floor_area_sqm']:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            # Fill missing with median
            median_val = self.df[col].median()
            self.df[col] = self.df[col].fillna(median_val)
            logger.info(f"Converted {col} to numeric")

        # Calculate new features
        self.df['price_per_sqm'] = self.df['resale_price'] / self.df['floor_area_sqm']
        logger.info("Calculated price_per_sqm")
        
        # Handle lease dates
        try:
            self.df['lease_commence_date'] = pd.to_datetime(
                self.df['lease_commence_date'], errors='coerce'
            )
            current_year = datetime.now().year
            self.df['lease_remaining'] = 99 - (current_year - self.df['lease_commence_date'].dt.year)
            logger.info("Calculated lease_remaining")
        except Exception as e:
            logger.error(f"Lease date error: {e}")
            self.df['lease_remaining'] = np.nan
        
        # Clean categorical data
        self.df['town'] = self.df['town'].str.title().str.strip()
        logger.info("Cleaned town names")
        
        # Filter outliers
        initial_count = len(self.df)
        self.df = self.df[
            (self.df['resale_price'] > 10000) & 
            (self.df['floor_area_sqm'] > 20)
        ]
        logger.info(f"Filtered {initial_count - len(self.df)} outliers")
        
        logger.info("Data cleaning completed")

    def _fallback_procedure(self):
        """Multi-stage fallback handling"""
        try:
            logger.warning("Primary methods failed, trying cache...")
            self._load_from_cache()
        except:
            logger.error("Cache load failed, generating sample data")
            self._generate_sample_data()

    def _generate_sample_data(self):  # UPDATED METHOD
        """Create sample dataset when all else fails"""
        logger.critical("GENERATING SAMPLE DATA - REAL DATA UNAVAILABLE")
        sample = {
            'month': ['2023-01', '2023-02'],
            'town': ['Ang Mo Kio', 'Bedok'],
            'resale_price': [400000, 420000],
            'floor_area_sqm': [80.0, 85.0],
            'flat_type': ['4 ROOM', '5 ROOM'],
            'lease_commence_date': [1985, 1990]  # ADDED FIELD
        }
        self.df = pd.DataFrame(sample)
        self._clean_data()

    # ----------------------
    # Query Methods for Backend
    # ----------------------
    
    def get_towns(self):
        """Get unique town names"""
        return sorted(self.df['town'].unique().tolist()) if self.df is not None else []
    
    def get_flat_types(self):
        """Get unique flat types"""
        return sorted(self.df['flat_type'].unique().tolist()) if self.df is not None else []
    
    def get_town_data(self, town):
        """Get data for specific town"""
        if self.df is None:
            return pd.DataFrame()
            
        town_data = self.df[self.df['town'] == town.title()].copy()
        
        # Aggregate monthly prices
        monthly_avg = town_data.groupby('month').agg({
            'resale_price': 'mean',
            'price_per_sqm': 'mean',
            'lease_remaining': 'mean'
        }).reset_index()
        
        return monthly_avg
    
    def get_full_data(self):
        """Get full dataset (use with caution for large data)"""
        return self.df.copy() if self.df is not None else pd.DataFrame()

# TEST THE FIXED PROCESSOR
if __name__ == "__main__":
    logger.info("Testing fixed data processor")
    try:
        processor = HDBDataProcessor()
        print("Sample data:")
        print(processor.df[['town', 'resale_price', 'price_per_sqm', 'lease_remaining']].head(2))
        print("\nSaving cache...")
        processor._save_cache()
        print("Processor initialized successfully!")
    except Exception as e:
        logger.critical(f"Critical failure: {e}")
        print("Processor failed completely")