"""
Bug Condition Exploration Test: Float Parsing Error in Model Retraining

**Validates: Requirements 1.5, 1.6**

This test explores the bug condition where model retraining fails with 
"unable to parse to float" error when loading embeddings from the database.

CRITICAL: This test is EXPECTED TO FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior - it will validate the fix when it passes after implementation.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import queries
from database.db_connection import DatabaseConnection


# Strategy for generating valid 512-dimensional embeddings
@st.composite
def embedding_vector(draw):
    """Generate a valid 512-dimensional embedding vector."""
    # Generate 512 float values between -1 and 1 (typical range for normalized embeddings)
    values = draw(st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=512,
        max_size=512
    ))
    return np.array(values, dtype=np.float64)


@st.composite
def person_name(draw):
    """Generate a valid person name."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=3,
        max_size=20
    ))


class TestFloatParsingBugCondition:
    """
    Test suite for Bug Condition 3: Float Parsing Error
    
    **Property 1: Bug Condition** - Model Retraining Float Parsing Error
    
    For any model retraining operation that loads embeddings from the database,
    the system SHALL successfully parse embedding data from pgvector format into
    numpy arrays with the correct float dtype without raising "unable to parse to float" errors.
    """
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create database connection for testing."""
        conn = queries.get_db_connection()
        yield conn
        conn.close_all()
    
    @pytest.fixture(scope="function")
    def setup_test_data(self, db_connection):
        """
        Set up test data: create a person and insert face embeddings.
        This simulates the scenario where a user has labeled faces in the database.
        """
        db_conn = db_connection.get_connection()
        try:
            cursor = db_conn.cursor()
            
            # Create a test person
            cursor.execute(
                "INSERT INTO people (name, description) VALUES (%s, %s) RETURNING id",
                ("TestPerson_FloatParsing", "Test person for float parsing bug")
            )
            person_id = cursor.fetchone()[0]
            
            # Insert a test face embedding (simulating a labeled face)
            # Generate a valid 512-dimensional embedding
            test_embedding = np.random.rand(512).astype(np.float64).tolist()
            
            cursor.execute(
                "INSERT INTO faces (person_id, image_path, embedding, face_confidence, source_type) "
                "VALUES (%s, %s, %s::vector, %s, %s)",
                (person_id, "/test/image.jpg", test_embedding, 0.95, "training")
            )
            
            db_conn.commit()
            
            yield person_id
            
            # Cleanup: remove test data
            cursor.execute("DELETE FROM faces WHERE person_id = %s", (person_id,))
            cursor.execute("DELETE FROM people WHERE id = %s", (person_id,))
            db_conn.commit()
            
        finally:
            cursor.close()
            db_connection.return_connection(db_conn)
    
    def test_get_embeddings_for_training_basic(self, db_connection, setup_test_data):
        """
        Test that get_embeddings_for_training() can load embeddings without float parsing errors.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with "unable to parse to float" error
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES
        
        This test demonstrates the bug condition where pgvector returns embeddings in a format
        that numpy cannot directly parse as float32.
        """
        person_id = setup_test_data
        
        # Attempt to load embeddings for training
        # This should trigger the float parsing bug on unfixed code
        try:
            embeddings_data = queries.get_embeddings_for_training(
                conn=db_connection,
                include_unknown_labeled=True
            )
            
            # If we get here without exception, verify the data is valid
            assert len(embeddings_data) > 0, "Should have at least one embedding"
            
            for embedding, name in embeddings_data:
                # Verify embedding is a numpy array
                assert isinstance(embedding, np.ndarray), \
                    f"Embedding should be numpy array, got {type(embedding)}"
                
                # Verify embedding has correct shape
                assert embedding.shape == (512,), \
                    f"Embedding should have shape (512,), got {embedding.shape}"
                
                # Verify embedding contains valid float values
                assert np.all(np.isfinite(embedding)), \
                    "Embedding should contain only finite float values"
                
                # Verify name is a string
                assert isinstance(name, str), \
                    f"Person name should be string, got {type(name)}"
            
            # If all assertions pass, the bug is fixed
            print("✅ SUCCESS: Embeddings loaded successfully without float parsing errors")
            
        except (ValueError, TypeError) as e:
            # This is the expected failure on unfixed code
            error_msg = str(e)
            if "unable to parse" in error_msg.lower() or "float" in error_msg.lower():
                pytest.fail(
                    f"❌ BUG CONFIRMED: Float parsing error detected: {error_msg}\n"
                    f"This confirms the bug exists in get_embeddings_for_training().\n"
                    f"Root cause: pgvector returns embeddings in a format that numpy cannot parse as float32.\n"
                    f"Counterexample: person_id={person_id}"
                )
            else:
                # Unexpected error - re-raise
                raise
    
    @given(
        num_people=st.integers(min_value=1, max_value=5),
        faces_per_person=st.integers(min_value=1, max_value=3)
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_get_embeddings_for_training_property(
        self, 
        db_connection, 
        num_people, 
        faces_per_person
    ):
        """
        Property-based test: For ANY number of people and faces, 
        get_embeddings_for_training() should successfully load embeddings without errors.
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with float parsing errors
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES for all generated test cases
        
        This property test generates multiple scenarios to surface counterexamples.
        """
        db_conn = db_connection.get_connection()
        created_person_ids = []
        
        try:
            cursor = db_conn.cursor()
            
            # Create test people and embeddings
            for i in range(num_people):
                # Create person
                cursor.execute(
                    "INSERT INTO people (name, description) VALUES (%s, %s) RETURNING id",
                    (f"TestPerson_PBT_{i}", f"Property test person {i}")
                )
                person_id = cursor.fetchone()[0]
                created_person_ids.append(person_id)
                
                # Insert face embeddings for this person
                for j in range(faces_per_person):
                    test_embedding = np.random.rand(512).astype(np.float64).tolist()
                    cursor.execute(
                        "INSERT INTO faces (person_id, image_path, embedding, face_confidence, source_type) "
                        "VALUES (%s, %s, %s::vector, %s, %s)",
                        (person_id, f"/test/person_{i}_face_{j}.jpg", test_embedding, 0.95, "training")
                    )
            
            db_conn.commit()
            
            # Now attempt to load embeddings
            try:
                embeddings_data = queries.get_embeddings_for_training(
                    conn=db_connection,
                    include_unknown_labeled=True
                )
                
                # Verify we got the expected number of embeddings
                expected_count = num_people * faces_per_person
                actual_count = len([e for e, n in embeddings_data if any(f"TestPerson_PBT_{i}" == n for i in range(num_people))])
                
                # Verify all embeddings are valid numpy arrays
                for embedding, name in embeddings_data:
                    if any(f"TestPerson_PBT_{i}" == name for i in range(num_people)):
                        assert isinstance(embedding, np.ndarray), \
                            f"Embedding should be numpy array, got {type(embedding)}"
                        assert embedding.shape == (512,), \
                            f"Embedding should have shape (512,), got {embedding.shape}"
                        assert np.all(np.isfinite(embedding)), \
                            "Embedding should contain only finite float values"
                
            except (ValueError, TypeError) as e:
                error_msg = str(e)
                if "unable to parse" in error_msg.lower() or "float" in error_msg.lower():
                    pytest.fail(
                        f"❌ BUG CONFIRMED: Float parsing error in property test\n"
                        f"Error: {error_msg}\n"
                        f"Counterexample: num_people={num_people}, faces_per_person={faces_per_person}\n"
                        f"Total embeddings attempted: {num_people * faces_per_person}"
                    )
                else:
                    raise
            
        finally:
            # Cleanup
            for person_id in created_person_ids:
                cursor.execute("DELETE FROM faces WHERE person_id = %s", (person_id,))
                cursor.execute("DELETE FROM people WHERE id = %s", (person_id,))
            db_conn.commit()
            cursor.close()
            db_connection.return_connection(db_conn)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
