
@app.route('/admin/update-record', methods=['POST'])
@login_required
def admin_update_record():
    """Update a passenger record (admin only)"""
    try:
        record_id = request.form.get('record_id')
        table_name = request.form.get('table_name')
        
        # Determine which table to update
        if table_name == 'passenger_insider' or 'insider' in table_name.lower():
            passenger = PassengerInsider.query.get(record_id)
            model = PassengerInsider
        else:
            passenger = PassengerOutsider.query.get(record_id)
            model = PassengerOutsider
        
        if not passenger:
            flash('Record not found', 'error')
            return redirect(url_for('admin_dashboard', table=table_name))
        
        # Update fields from form
        for key, value in request.form.items():
            if key not in ['record_id', 'table_name'] and hasattr(passenger, key.lower().replace(' ', '_')):
                setattr(passenger, key.lower().replace(' ', '_'), value)
        
        db.session.commit()
        flash('Record updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating record: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard', table=table_name))


@app.route('/admin/delete-record', methods=['POST'])
@login_required
def admin_delete_record():
    """Delete a passenger record (admin only)"""
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        table_name = data.get('table_name')
        
        # Determine which table to delete from
        if table_name == 'passenger_insider' or 'insider' in table_name.lower():
            passenger = PassengerInsider.query.get(record_id)
        else:
            passenger = PassengerOutsider.query.get(record_id)
        
        if not passenger:
            return jsonify({'success': False, 'message': 'Record not found'})
        
        db.session.delete(passenger)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
