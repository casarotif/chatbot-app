from flask import Blueprint, request, jsonify, render_template
from app.utils import generate_response, response_generator

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@main.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        response = generate_response(user_message)
        
        return jsonify({
            'response': response,
            'conversation_length': len(response_generator.conversation_history) // 2
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/clear-history', methods=['POST'])
def clear_history():
    """Limpa o histórico da conversa"""
    response_generator.conversation_history = []
    return jsonify({'message': 'Histórico limpo com sucesso'})