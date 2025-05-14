// Sample JavaScript file for testing LLM parsing

// Imports
import React from 'react';
import { useState, useEffect } from 'react';

// Class definition
class TestComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      count: 0,
      items: []
    };
  }

  // Method
  incrementCount() {
    this.setState({ count: this.state.count + 1 });
  }

  // Another method
  resetCount() {
    this.setState({ count: 0 });
  }

  render() {
    return (
      <div>
        <h1>Count: {this.state.count}</h1>
        <button onClick={() => this.incrementCount()}>Increment</button>
        <button onClick={() => this.resetCount()}>Reset</button>
      </div>
    );
  }
}

// Function definition
function formatName(user) {
  return user.firstName + ' ' + user.lastName;
}

// Arrow function
const getGreeting = (user) => {
  if (user) {
    return <h1>Hello, {formatName(user)}!</h1>;
  }
  return <h1>Hello, Stranger.</h1>;
};

// Export
export default TestComponent;
export { formatName, getGreeting };
