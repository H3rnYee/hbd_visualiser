# app.py
from flask import Flask, jsonify, render_template
from data_processor import HDBDataProcessor #vercel entry

app = Flask(__name__)

processor = HDBDataProcessor(use_api=False, cache_file='hdb_data.parquet')

@app.route('/')
def index():
    """Main visualization dashboard"""
    return render_template('index.html')


@app.route('/towns')
def get_towns():
    """Get list of available towns"""
    if not processor:
        return jsonify(["Ang Mo Kio", "Bedok"])  # Fallback
    return jsonify(processor.get_towns())

@app.route('/town/<town_name>')
def get_town_data(town_name):
    """Get aggregated data for a town"""
    if not processor:
        # Sample data fallback
        return jsonify([
            {"month": "2023-01", "resale_price": 400000, "price_per_sqm": 5000},
            {"month": "2023-02", "resale_price": 420000, "price_per_sqm": 4941}
        ])
    
    town_data = processor.get_town_data(town_name)
    return jsonify(town_data.to_dict(orient='records'))

@app.route('/heatmap')
def get_heatmap_data():
    """Get data for price heatmap"""
    if not processor:
        return jsonify([])
    
    # Aggregate by town and flat type
    heatmap_data = processor.df.groupby(['town', 'flat_type']).agg({
        'price_per_sqm': 'median'
    }).reset_index()
    
    return jsonify(heatmap_data.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)